"""Dataset-reference card-rank recognition for testing and webcam use."""

import argparse
import csv
import json
import time
from pathlib import Path

import cv2
import numpy as np


RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
RANK_VALUES = {
    "A": (1, 11),
    "J": (10,),
    "Q": (10,),
    "K": (10,),
    "2": (2,),
    "3": (3,),
    "4": (4,),
    "5": (5,),
    "6": (6,),
    "7": (7,),
    "8": (8,),
    "9": (9,),
    "10": (10,),
}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "dataset"

ROI_X = 0.50
ROI_Y = 0.05
ROI_WIDTH = 0.45
ROI_HEIGHT = 0.65
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
DISPLAY_WIDTH = 480
DISPLAY_HEIGHT = 360


def read_image(path: str | Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {path}")
    return image


def correct_orientation(image: np.ndarray) -> np.ndarray:
    """Keep the supplied card image upright for matching."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def extract_features(image: np.ndarray) -> tuple[tuple[np.ndarray, np.ndarray], float]:
    """Extract right-side rank and red-suit features from an upright image."""
    height, width = image.shape[:2]
    x1 = int(width * ROI_X)
    y1 = int(height * ROI_Y)
    x2 = int(width * (ROI_X + ROI_WIDTH))
    y2 = int(height * (ROI_Y + ROI_HEIGHT))
    roi = image[y1:y2, x1:x2]
    if roi.size == 0:
        raise ValueError("Card ROI is empty")

    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    red = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    red_mask = cv2.inRange(
        red,
        np.array([0, 70, 70], dtype=np.uint8),
        np.array([20, 255, 255], dtype=np.uint8),
    )

    gray_edge = cv2.Canny(gray, 50, 150)
    red_edge = cv2.resize(red_mask, (128, 128), interpolation=cv2.INTER_AREA)
    channels = (
        gray_edge.astype(np.float32) / 255.0,
        red_edge.astype(np.float32) / 255.0,
    )

    red_ratio = float(
        np.count_nonzero(red_mask) / max(1, red_mask.shape[0] * red_mask.shape[1])
    )
    return channels, red_ratio


def load_references(
    dataset_dir: str | Path,
) -> list[tuple[Path, str, str, tuple[np.ndarray, np.ndarray], float]]:
    dataset_dir = Path(dataset_dir)
    references = []
    for path in sorted(dataset_dir.glob("*/*")):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        parts = path.parent.name.rsplit("_", 1)
        if (
            len(parts) != 2
            or parts[0] not in RANKS
            or parts[1] not in {"red", "black"}
        ):
            continue
        upright = correct_orientation(read_image(path))
        channels, red_ratio = extract_features(upright)
        references.append((path, parts[0], parts[1], channels, red_ratio))
    if not references:
        raise FileNotFoundError(
            f"No references found in {dataset_dir}/<rank>_<color>/"
        )
    return references


def similarity(feature_a: np.ndarray, feature_b: np.ndarray) -> float:
    return float(np.mean(feature_a * feature_b))


def recognize_upright(
    upright: np.ndarray,
    references: list,
    threshold: float = 0.50,
    margin: float = 0.025,
    exclude: Path | None = None,
) -> dict:
    """Recognize an already upright image against labeled dataset references."""
    channels, red_ratio = extract_features(upright)
    options = []
    for path, rank, color, reference_channels, reference_red_ratio in references:
        if exclude is not None and path == exclude:
            continue
        score = (
            0.70 * similarity(channels[0], reference_channels[0])
            + 0.30 * similarity(channels[1], reference_channels[1])
            - 0.50 * abs(red_ratio - reference_red_ratio)
        )
        options.append((score, rank, color, str(path)))
    if not options:
        raise ValueError("No reference images available for matching")

    options.sort(reverse=True)
    best = options[0]
    runner = next(
        (option for option in options[1:] if option[1:3] != best[1:3]),
        None,
    )
    runner_score = runner[0] if runner else -1.0
    separation = best[0] - runner_score
    needed_margin = max(margin, 0.045) if best[1] in {"6", "9"} else margin
    return {
        "rank": best[1],
        "color": best[2],
        "score": round(best[0], 5),
        "margin": round(separation, 5),
        "status": (
            "ok"
            if best[0] >= threshold and separation >= needed_margin
            else "review"
        ),
        "reference": best[3],
    }


def process_photo(
    image: np.ndarray,
    references: list,
    save_path: str | Path | None = None,
) -> dict:
    upright = correct_orientation(image)
    result = recognize_upright(upright, references)
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(save_path), cv2.cvtColor(upright, cv2.COLOR_RGB2BGR)):
            raise OSError(f"Unable to save {save_path}")
        result["corrected_image"] = str(save_path)
    return result


def test_dataset(
    dataset_dir: str | Path,
    references: list,
    csv_path: str | Path,
) -> None:
    records = []
    for path, rank, color, *_ in references:
        upright = correct_orientation(read_image(path))
        result = recognize_upright(upright, references)
        records.append(
            {
                "file": str(path),
                "actual": f"{rank}_{color}",
                "predicted": f'{result["rank"]}_{result["color"]}',
                "correct": result["rank"] == rank and result["color"] == color,
                "status": result["status"],
                "score": result["score"],
            }
        )

    correct = sum(record["correct"] for record in records)
    print(f"IN-SAMPLE reference matching: {correct}/{len(records)} correct")

    leave_one_out = []
    for path, rank, color, *_ in references:
        same_label_count = sum(
            1 for _, ref_rank, ref_color, *_ in references
            if (ref_rank, ref_color) == (rank, color)
        )
        if same_label_count < 2:
            continue
        result = recognize_upright(
            correct_orientation(read_image(path)),
            references,
            exclude=path,
        )
        leave_one_out.append(
            (
                path.name,
                f"{rank}_{color}",
                f'{result["rank"]}_{result["color"]}',
                result["status"],
            )
        )

    leave_one_out_correct = sum(
        actual == predicted
        for _, actual, predicted, _ in leave_one_out
    )
    print(
        "LEAVE-ONE-OUT where possible: "
        f"{leave_one_out_correct}/{len(leave_one_out)} correct"
    )
    for name, actual, predicted, status in leave_one_out:
        print(
            f"  {name}: actual {actual}, "
            f"predicted {predicted} ({status})"
        )

    print(
        "CAUTION: in-sample matching is not evidence of reliable "
        "recognition on NEW captures."
    )
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"Results CSV: {csv_path}")


class VisionCardReader:
    """Recognize card ranks from images or a camera using dataset references."""

    def __init__(
        self,
        camera_number: int = 0,
        dataset: str | Path = DEFAULT_DATASET,
    ) -> None:
        self.references = load_references(dataset)
        self.camera = cv2.VideoCapture(camera_number)
        if not self.camera.isOpened():
            self.camera.release()
            raise RuntimeError(f"Could not open camera {camera_number}.")
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    def recognize_image(self, image: np.ndarray) -> dict:
        return process_photo(image, self.references)

    def read_card(self) -> tuple[str, tuple[int, ...]]:
        success, frame = self.camera.read()
        if not success:
            raise RuntimeError("Could not read a frame from the camera.")
        result = self.recognize_image(frame)
        if result["status"] != "ok":
            raise ValueError(
                f"Card recognition needs review: "
                f"{result['rank']} {result['color']} "
                f"(score {result['score']}, margin {result['margin']})."
            )
        rank = result["rank"]
        return rank, RANK_VALUES[rank]

    def close(self) -> None:
        self.camera.release()
        cv2.destroyAllWindows()

    def __enter__(self) -> "VisionCardReader":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def read_rank(image: np.ndarray, dataset: str | Path = DEFAULT_DATASET) -> tuple[str, tuple[int, ...]]:
    references = load_references(dataset)
    result = process_photo(image, references)
    if result["status"] != "ok":
        raise ValueError(
            f"Card recognition needs review: "
            f"{result['rank']} {result['color']} "
            f"(score {result['score']}, margin {result['margin']})."
        )
    return result["rank"], RANK_VALUES[result["rank"]]


def draw_roi(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    top_left = (int(width * ROI_X), int(height * ROI_Y))
    bottom_right = (
        int(width * (ROI_X + ROI_WIDTH)),
        int(height * (ROI_Y + ROI_HEIGHT)),
    )
    result = image.copy()
    cv2.rectangle(result, top_left, bottom_right, (0, 255, 0), 2)
    cv2.putText(
        result,
        "Place card here",
        (top_left[0], max(25, top_left[1] - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true", help="capture one Raspberry Pi camera image")
    mode.add_argument("--image", type=Path, help="recognize an existing image")
    mode.add_argument("--test", action="store_true", help="evaluate labeled dataset images")
    mode.add_argument("--camera", action="store_true", help="open an interactive webcam")
    parser.add_argument("--camera-number", type=int, default=0)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )
    parser.add_argument("--output", type=Path, default=Path("corrected_card.jpg"))
    args = parser.parse_args()

    references = load_references(args.dataset)
    print(f"Loaded {len(references)} reference images")
    if args.test:
        test_dataset(args.dataset, references, Path("card_test_results.csv"))
        return

    if args.capture:
        try:
            from picamera2 import Picamera2
        except ImportError as error:
            raise SystemExit(
                "Picamera2 is required for --capture"
            ) from error
        camera = Picamera2()
        try:
            camera.configure(camera.create_still_configuration())
            camera.start()
            time.sleep(2)
            photo_path = Path("capture_card.jpg")
            camera.capture_file(str(photo_path))
            photo = read_image(photo_path)
        finally:
            camera.stop()
            camera.close()
    elif args.image:
        photo = read_image(args.image)
    else:
        photo = None

    if args.camera:
        with VisionCardReader(args.camera_number, args.dataset) as reader:
            print("Press SPACE to recognize; press Q to quit.")
            while True:
                success, frame = reader.camera.read()
                if not success:
                    raise SystemExit("Could not read a frame from the camera.")
                cv2.imshow(
                    "Card reader",
                    cv2.resize(
                        draw_roi(frame),
                        (DISPLAY_WIDTH, DISPLAY_HEIGHT),
                        interpolation=cv2.INTER_AREA,
                    ),
                )
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord(" "):
                    print(json.dumps(reader.recognize_image(frame), indent=2))
        return

    result = process_photo(photo, references, args.output)
    print(json.dumps(result, indent=2))
    if result["status"] != "ok":
        raise SystemExit("Card recognition status is review")


if __name__ == "__main__":
    main()

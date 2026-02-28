from PIL import Image
import sys

def check_image(path):
    try:
        img = Image.open(path).convert('RGB')
        extrema = img.getextrema()
        print(f"{path}: Extrema = {extrema}")
        if extrema[0][0] == extrema[0][1] and extrema[1][0] == extrema[1][1] and extrema[2][0] == extrema[2][1]:
            print("Image is uniform (single color).")
        else:
            print("Image has content.")
    except Exception as e:
        print(f"Failed to check {path}: {e}")

check_image("src/nlp2cmd/jspaint_test.png")
check_image("src/nlp2cmd/jspaint_mouse_test.png")
check_image("recordings/action_plan_final_20260228_134736.png")

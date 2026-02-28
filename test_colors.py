from PIL import Image
import sys

def analyze(path):
    img = Image.open(path).convert('RGB')
    colors = img.getcolors(maxcolors=1000000)
    print(f"{path}: {len(colors)} unique colors")
    # let's see if red is there
    reds = [c for c in colors if c[1][0] > 200 and c[1][1] < 50 and c[1][2] < 50]
    if reds:
        print(f"Red pixels found: {sum(c[0] for c in reds)}")
    else:
        print("No red pixels found")

analyze("src/nlp2cmd/jspaint_test.png")
analyze("src/nlp2cmd/jspaint_mouse_test.png")
analyze("recordings/action_plan_final_20260228_134736.png")

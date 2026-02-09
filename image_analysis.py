import torch
from PIL import Image
import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import sys

sys.path.append("FastSAM")
from fastsam import FastSAM, FastSAMPrompt

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

def detect_coffee_ring(model, img_path, result_dir):
    img_src = cv2.imread(img_path, cv2.IMREAD_COLOR)
    img_gray = cv2.cvtColor(img_src, cv2.COLOR_BGR2GRAY)

    size = 600
    x = int(img_src.shape[1]/2 - size/2)
    y = int(img_src.shape[0]/2 - size/2)
    crop_img = img_src[y:y+size, x:x+size]

    root, ext = os.path.splitext(os.path.basename(img_path))
    root = os.path.join(result_dir, root)
    crop_path = root + "_crop" + ext
    cv2.imwrite(crop_path, crop_img)

    kernel = 7
    img_blur = cv2.GaussianBlur(crop_img, (kernel, kernel), None)

    img_edge = cv2.Canny(img_blur, threshold1=90, threshold2=60)

    circles = cv2.HoughCircles(img_edge, cv2.HOUGH_GRADIENT,
                               dp=1,
                               minDist=100,
                               param1=100,
                               param2=80,
                               minRadius=200,
                               maxRadius=400,
                              )
    
    if circles is not None:
      circles = np.uint16(np.around(circles))
      x, y, r = circles[0][0][:3]
    else:
      print("Failed to detect circle")
      x, y, r = 300, 300, 220

    points = [[x, y],[x, int(y-r*0.8)]]
    cv2.circle(crop_img, (x, y), r, (0, 255, 255), 3)
    cv2.circle(crop_img, (x, y), 3, (0, 0, 255), -1)
    cv2.imwrite(root + "_cirlcle" + ext, crop_img)
    
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )
    input = Image.open(crop_path)
    input = input.convert("RGB")
    everything_results = model(
        input,
        device=device,
        retina_masks=True,
        imgsz=1024,
        conf=0.4,
        iou=0.9    
    )
    prompt_process = FastSAMPrompt(input, everything_results, device=device)

    point_label = [1, 0]
    ann = prompt_process.point_prompt(
          points=points, pointlabel=point_label
    )

    bboxes = None
    
    prompt_process.plot(
        annotations=ann,
        output_path=os.path.join("output", os.path.basename(img_path)),
        bboxes = bboxes,
        points = points,
        point_label = point_label,
        withContours=False,
        better_quality=False,
        mask_random_color=False
    )

    mask = ann[0].astype(np.uint8)

    img_draw = cv2.imread(crop_path, cv2.IMREAD_COLOR)
    x = points[0][0]
    y = points[0][1]
    cv2.circle(img_draw, (x, y), 2, (0, 255, 0), -1)

    x = points[1][0]
    y = points[1][1]
    cv2.circle(img_draw, (x, y), 2, (0, 0, 255), -1)

    cv2.imwrite(root + "_points" + ext, img_draw)
    # Generate inner and mask based on ellipse
    inner_mask = np.zeros_like(mask)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    if not contours:
         print("Failed to find contours")
         return 0.0
    
    ellipse = cv2.fitEllipse(contours[0])
    ((cx, cy), (h, w), deg) = ellipse
    inner_ellipse = ((cx, cy), (h*0.8, w*0.8), deg)
    cv2.ellipse(inner_mask, inner_ellipse, color=1, thickness=-1)
    outer_mask = cv2.bitwise_xor(mask, inner_mask)

    gray_img = cv2.imread(crop_path, cv2.IMREAD_GRAYSCALE)

    inner_img = gray_img[inner_mask == 1]
    outer_img = gray_img[outer_mask == 1]

    plt.hist(outer_img, bins=30, alpha=0.5, label="Outer")
    plt.hist(inner_img, bins=30, alpha=0.5, label="Inner")

    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.title("Overlayed Histograms")
    plt.legend()
    plt.savefig(root + "_hist" + ext)
    plt.clf()
    
    ring_value = np.mean(inner_img) + np.std(inner_img)
    ratio = np.sum(outer_img > ring_value) / len(outer_img)

    outer_masked_img = cv2.bitwise_and(gray_img, gray_img, mask=outer_mask*255)
    inner_masked_img = cv2.bitwise_and(gray_img, gray_img, mask=inner_mask*255)
    cv2.imwrite(root + "_inner" + ext, inner_masked_img)
    cv2.imwrite(root + "_outer" + ext, outer_masked_img)

    img = cv2.imread(crop_path, cv2.IMREAD_COLOR)
    color_mask = np.zeros_like(img)
    color_mask[(inner_mask == 1)] = [0, 0, 255]
    overlay = cv2.addWeighted(img, 1.0, color_mask, 0.3, 0)
    result = cv2.ellipse(overlay, ellipse, (0,255,0), 2)
    cv2.imwrite(root + "_result" + ext, result)

    return ratio
import numpy as np
def filter_and_merge_segments(masks, min_area=15000, iou_thresh=0.9, merge_thresh=0.3):
    """
    Filter, deduplicate, and merge partial segments. 
    Allows to narrow down to distinct objects.
    - min_area : minimum area in pixels
    - iou_thresh : inclusion threshold to remove duplicates
    - merge_thresh : IoU threshold to merge two partial masks
    """
    # Step 1: Filter by area
    filtered = []
    for mask in masks:
        seg = mask["segmentation"].astype(np.uint8)
        area = np.sum(seg)
        if area >= min_area:
            filtered.append(seg)

    # Step 2: Remove duplicates (inclusions)
    unique_masks = []
    for i, seg1 in enumerate(filtered):
        keep = True
        for j, seg2 in enumerate(filtered):
            if i == j:
                continue
            inter = np.logical_and(seg1, seg2).sum()
            area1 = seg1.sum()
            if area1 > 0 and inter / area1 > iou_thresh:
                keep = False
                break
        if keep:
            unique_masks.append(seg1)

    # Step 3: Merge overlapping masks
    merged = []
    used = [False] * len(unique_masks)

    for i in range(len(unique_masks)):
        if used[i]:
            continue
        seg_i = unique_masks[i].copy()
        for j in range(i + 1, len(unique_masks)):
            if used[j]:
                continue
            seg_j = unique_masks[j]
            inter = np.logical_and(seg_i, seg_j).sum()
            union = np.logical_or(seg_i, seg_j).sum()
            iou = inter / union if union > 0 else 0
            if iou > merge_thresh:
                # Fusion → OR logique
                seg_i = np.logical_or(seg_i, seg_j).astype(np.uint8)
                used[j] = True
        merged.append(seg_i)
        used[i] = True

    # Build final list of masks
    final_masks = [{"segmentation": m.astype(np.uint8)} for m in merged]
    return final_masks
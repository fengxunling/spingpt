if "view":
    from utils.modules.viewer import display_nifti_slice
    viewer_prompt = f"which one is most relevant: sagittal, axial, coronal?"
    # view_plane = input(viewer_prompt)
    slice_idx_promt = f"which slice index does the user want to view? If not clearly specified, please infer which index is the most relevant to display."
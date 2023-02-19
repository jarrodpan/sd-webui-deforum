# This helper script is responsible for ControlNet/Deforum integration
# https://github.com/Mikubill/sd-webui-controlnet — controlnet repo

import os, sys
import gradio as gr

has_controlnet = None

def find_controlnet():
    global has_controlnet
    if has_controlnet is not None:
        return has_controlnet
    
    try:
        from scripts import controlnet
    except Exception as e:
        print(f'Failed to import controlnet! The exact error is {e}. Deforum support for ControlNet will not be activated')
        has_controlnet = False
        return False
    has_controlnet = True
    print(f'Congratulations! You have ControlNet support for Deforum enabled!') # TODO: make green
    return True

# The most parts below are plainly copied from controlnet.py
# TODO: come up with a cleaner way

gradio_compat = True
try:
    from distutils.version import LooseVersion
    from importlib_metadata import version
    if LooseVersion(version("gradio")) < LooseVersion("3.10"):
        gradio_compat = False
except ImportError:
    pass

# svgsupports
svgsupport = False
try:
    import io
    import base64
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    svgsupport = True
except ImportError:
    pass

def setup_controlnet_ui_raw():
    from scripts import controlnet
    from scripts.controlnet import update_cn_models, cn_models, cn_models_names

    model_dropdowns = []
    infotext_fields = []

    # Already under an accordion

    # Video input to be fed into ControlNet
    #input_video_url = gr.Textbox(source='upload', type='numpy', tool='sketch') # TODO
    with gr.Row():
        input_video_chosen_file = gr.File(label="ControlNet Video input", interactive=True, file_count="single", file_types=["video"], elem_id="controlnet_input_video_chosen_file")

    # Copying the main ControlNet widgets while getting rid of static elements such as the scribble pad
    with gr.Row():
        enabled = gr.Checkbox(label='Enable', value=False)
        scribble_mode = gr.Checkbox(label='Scribble Mode (Invert colors)', value=False)
        rgbbgr_mode = gr.Checkbox(label='RGB to BGR', value=False)
        lowvram = gr.Checkbox(label='Low VRAM', value=False)

    # Main part
    class ToolButton(gr.Button, gr.components.FormComponent):
        """Small button with single emoji as text, fits inside gradio forms"""

        def __init__(self, **kwargs):
            super().__init__(variant="tool", **kwargs)

        def get_block_name(self):
            return "button"

    from scripts.processor import canny, midas, midas_normal, leres, hed, mlsd, openpose, pidinet, simple_scribble, fake_scribble, uniformer

    preprocessor = {
        "none": lambda x, *args, **kwargs: x,
        "canny": canny,
        "depth": midas,
        "depth_leres": leres,
        "hed": hed,
        "mlsd": mlsd,
        "normal_map": midas_normal,
        "openpose": openpose,
        # "openpose_hand": openpose_hand,
        "pidinet": pidinet,
        "scribble": simple_scribble,
        "fake_scribble": fake_scribble,
        "segmentation": uniformer,
    }

    def refresh_all_models(*inputs):
        update_cn_models()
        
        dd = inputs[0]
        selected = dd if dd in cn_models else "None"
        return gr.Dropdown.update(value=selected, choices=list(cn_models.keys()))

    refresh_symbol = '\U0001f504'  # 🔄
    switch_values_symbol = '\U000021C5' # ⇅

    with gr.Row():
        module = gr.Dropdown(list(preprocessor.keys()), label=f"Preprocessor", value="none")
        model = gr.Dropdown(list(cn_models.keys()), label=f"Model", value="None")
        refresh_models = ToolButton(value=refresh_symbol)
        refresh_models.click(refresh_all_models, model, model)
        # ctrls += (refresh_models, )
    with gr.Row():
        weight = gr.Slider(label=f"Weight", value=1.0, minimum=0.0, maximum=2.0, step=.05)
        guidance_strength =  gr.Slider(label="Guidance strength (T)", value=1.0, minimum=0.0, maximum=1.0, interactive=True)

        # ctrls += (module, model, weight,)
        # model_dropdowns.append(model)
        
    def build_sliders(module):
        if module == "canny":
            return [
                gr.update(label="Annotator resolution", value=512, minimum=64, maximum=2048, step=1, interactive=True),
                gr.update(label="Canny low threshold", minimum=1, maximum=255, value=100, step=1, interactive=True),
                gr.update(label="Canny high threshold", minimum=1, maximum=255, value=200, step=1, interactive=True),
                gr.update(visible=True)
            ]
        elif module == "mlsd": #Hough
            return [
                gr.update(label="Hough Resolution", minimum=64, maximum=2048, value=512, step=1, interactive=True),
                gr.update(label="Hough value threshold (MLSD)", minimum=0.01, maximum=2.0, value=0.1, step=0.01, interactive=True),
                gr.update(label="Hough distance threshold (MLSD)", minimum=0.01, maximum=20.0, value=0.1, step=0.01, interactive=True),
                gr.update(visible=True)
            ]
        elif module in ["hed", "fake_scribble"]:
            return [
                gr.update(label="HED Resolution", minimum=64, maximum=2048, value=512, step=1, interactive=True),
                gr.update(label="Threshold A", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(visible=True)
            ]
        elif module in ["openpose", "openpose_hand", "segmentation"]:
            return [
                gr.update(label="Annotator Resolution", minimum=64, maximum=2048, value=512, step=1, interactive=True),
                gr.update(label="Threshold A", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(visible=True)
            ]
        elif module == "depth":
            return [
                gr.update(label="Midas Resolution", minimum=64, maximum=2048, value=384, step=1, interactive=True),
                gr.update(label="Threshold A", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(visible=True)
            ]
        elif module == "depth_leres":
            return [
                gr.update(label="LeReS Resolution", minimum=64, maximum=2048, value=512, step=1, interactive=True),
                gr.update(label="Remove Near %", value=0, minimum=0, maximum=100, step=0.1, interactive=True),
                gr.update(label="Remove Background %", value=0, minimum=0, maximum=100, step=0.1, interactive=True),
                gr.update(visible=True)
            ]
        elif module == "normal_map":
            return [
                gr.update(label="Normal Resolution", minimum=64, maximum=2048, value=512, step=1, interactive=True),
                gr.update(label="Normal background threshold", minimum=0.0, maximum=1.0, value=0.4, step=0.01, interactive=True),
                gr.update(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(visible=True)
            ]
        elif module == "none":
            return [
                gr.update(label="Normal Resolution", value=64, minimum=64, maximum=2048, interactive=False),
                gr.update(label="Threshold A", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(visible=False)
            ]
        else:
            return [
                gr.update(label="Annotator resolution", value=512, minimum=64, maximum=2048, step=1, interactive=True),
                gr.update(label="Threshold A", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False),
                gr.update(visible=True)
            ]
        
    # advanced options    
    advanced = gr.Column(visible=False)
    with advanced:
        processor_res = gr.Slider(label="Annotator resolution", value=64, minimum=64, maximum=2048, interactive=False)
        threshold_a =  gr.Slider(label="Threshold A", value=64, minimum=64, maximum=1024, interactive=False)
        threshold_b =  gr.Slider(label="Threshold B", value=64, minimum=64, maximum=1024, interactive=False)
    
    if gradio_compat:    
        module.change(build_sliders, inputs=[module], outputs=[processor_res, threshold_a, threshold_b, advanced])
        
    infotext_fields.extend([
        (module, f"ControlNet Preprocessor"),
        (model, f"ControlNet Model"),
        (weight, f"ControlNet Weight"),
    ])

    # def svgPreprocess(inputs):
    #     if (inputs):
    #         if (inputs['image'].startswith("data:image/svg+xml;base64,") and svgsupport):
    #             svg_data = base64.b64decode(inputs['image'].replace('data:image/svg+xml;base64,',''))
    #             drawing = svg2rlg(io.BytesIO(svg_data))
    #             png_data = renderPM.drawToString(drawing, fmt='PNG')
    #             encoded_string = base64.b64encode(png_data)
    #             base64_str = str(encoded_string, "utf-8")
    #             base64_str = "data:image/png;base64,"+ base64_str
    #             inputs['image'] = base64_str
    #         return input_image.orgpreprocess(inputs)
    #     return None

    resize_mode = gr.Radio(choices=["Envelope (Outer Fit)", "Scale to Fit (Inner Fit)", "Just Resize"], value="Scale to Fit (Inner Fit)", label="Resize Mode")

    return locals()

def setup_controlnet_ui():
    if not find_controlnet():
        gr.HTML("""
                <a style='color:red;' target='_blank' href='https://github.com/Mikubill/sd-webui-controlnet'>ControlNet not found! Please, install it</a>
                """)
        return {}

    args_dict = setup_controlnet_ui_raw()
    ret_dict = {}

    for k, v in args_dict.items():
        ret_dict["controlnet_" + k] = v
    
    return ret_dict


def controlnet_component_names():
    if not find_controlnet():
        return []

    controlnet_args_names = str(r'''use_looper, init_images, image_strength_schedule, blendFactorMax, blendFactorSlope, 
            tweening_frames_schedule, color_correction_factor'''
    ).replace("\n", "").replace("\r", "").replace(" ", "").split(',')
    
    return controlnet_args_names

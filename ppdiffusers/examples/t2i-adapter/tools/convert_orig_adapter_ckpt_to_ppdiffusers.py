import argparse
from collections import OrderedDict
import sys
import paddle
import torch
from fastcore.all import patch_to, TypeDispatch
import json

from traitlets import default
def read_json(file):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def convert_to_paddle(vae_or_unet, dtype="float32"):
    need_transpose = []
    for k, v in vae_or_unet.named_modules():
        if isinstance(v, torch.nn.Linear):
            need_transpose.append(k + ".weight")
    new_vae_or_unet = OrderedDict()
    for k, v in vae_or_unet.state_dict().items():
        if k not in need_transpose:
            new_vae_or_unet[k] = v.cpu().numpy().astype(dtype)
        else:
            new_vae_or_unet[k] = v.t().cpu().numpy().astype(dtype)
    return new_vae_or_unet
  
  
@patch_to(paddle.nn.Layer)
def load_state_dict(self: paddle.nn.Layer, state_dict: dict, use_structured_name=True, strict=True):
    orig = self.state_dict()
    orig_keys = set([k for k in orig.keys()])
    loaded_keys = set([k for k in state_dict.keys()])

    missing_keys = list(orig_keys - loaded_keys)
    unexpected_keys = list(loaded_keys - orig_keys)
    print(f"missing_keys: {missing_keys}")
    print(f"unexpected_keys: {unexpected_keys}")
    if strict and (len(missing_keys) > 0 or len(unexpected_keys) > 0):
        raise ValueError("state_dict donot match the orignial state_dict!")
    return self.load_dict(state_dict, use_structured_name=use_structured_name)
  
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pytorch model weights to Paddle model weights.")
    
    parser.add_argument(
        "--orig_t2i_adapter_project_path",
        type=str,
        default="pytorch/T2I-Adapter",
        help="Path to a torch model parameters file",
    )
    parser.add_argument(
        "--orig_t2i_adapter_pretrained_ckpt_path",
        type=str,
        default="ckpt/t2iadapter_openpose_sd14v1.pth",
        help="Path to a torch model parameters file",
    )
    parser.add_argument(
        "--ppdiffusers_t2i_adapter_model_config_path",
        type=str,
        default="ppdiffusers/examples/t2i-adapter/config/openpose_adapter.json",
        help="Path to a torch model parameters file",
    )
    parser.add_argument(
        "--ppdiffusers_t2i_adapter_model_output_path",
        type=str,
        default="paddle_models/sd-v1-4-adapter-openpose_initialized",
        help="The model output path.",
    )
    args = parser.parse_args()
    
    import os, sys
    sys.path.append(args.orig_t2i_adapter_project_path)
    from ldm.modules.encoders.adapter import Adapter as torch_network
    Torch_Model = torch_network(cin=int(3*64), channels=[320, 640, 1280, 1280][:4], nums_rb=2, ksize=1, sk=True, use_conv=False)
    from ppdiffusers import Adapter as paddle_network
    Paddle_Model = paddle_network(**read_json(args.ppdiffusers_t2i_adapter_model_config_path))

    torch_model = Torch_Model
    if args.orig_t2i_adapter_pretrained_ckpt_path:
        torch_model.load_state_dict(torch.load(args.orig_t2i_adapter_pretrained_ckpt_path, map_location=torch.device('cpu')), strict=True)
    else:
        torch.save(torch_model.state_dict(), os.path.join(args.orig_t2i_adapter_project_path, "ckpt", "torch_t2i_model_initialized.pth"))
    numpy_state_dict = convert_to_paddle(torch_model)
    paddle_model = Paddle_Model
    paddle_model.load_state_dict(numpy_state_dict)
    paddle_model.save_pretrained(args.ppdiffusers_t2i_adapter_model_output_path)

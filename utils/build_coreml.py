import sys
import os
import torch
import coremltools as ct
from spandrel import ModelLoader


def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python3 build_coreml.py <path_to_weights.pth>")
        sys.exit(1)

    weights_path = sys.argv[1]

    if not os.path.exists(weights_path):
        print(f"❌ Error: Could not find file at {weights_path}")
        sys.exit(1)

    print(f"🧠 Loading Spandrel Architecture for: {os.path.basename(weights_path)}...")

    loader = ModelLoader()
    model_descriptor = loader.load_from_file(weights_path)
    model = model_descriptor.model
    model.eval()

    print(f"📐 Tracing the {model_descriptor.architecture} network...")
    dummy_input = torch.rand(1, 3, 360, 640)
    traced_model = torch.jit.trace(model, dummy_input)

    image_input = ct.ImageType(
        name="image",
        shape=(
            1,
            3,
            ct.RangeDim(lower_bound=64, upper_bound=3840),
            ct.RangeDim(lower_bound=64, upper_bound=2160),
        ),
        color_layout=ct.colorlayout.RGB,
    )

    print("🍏 Compiling into Apple .mlpackage (This might take a few minutes)...")
    mlmodel = ct.convert(
        traced_model,
        inputs=[image_input],
        convert_to="mlprogram",
        compute_units=ct.ComputeUnit.ALL,
    )

    os.makedirs("models", exist_ok=True)
    out_name = os.path.splitext(os.path.basename(weights_path))[0] + ".mlpackage"
    out_path = os.path.join("models", out_name)

    mlmodel.save(out_path)
    print(f"🎉 Success! Apple Native AI Model saved to: {out_path}")


if __name__ == "__main__":
    main()

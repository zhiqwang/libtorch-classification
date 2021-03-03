import io
import torch

# onnxruntime requires python 3.5 or above
try:
    import onnxruntime
except ImportError:
    onnxruntime = None

import unittest
from torchvision.ops._register_onnx_ops import _onnx_opset_version

from yolort.models import yolov5s, yolov5m, yolotr


@unittest.skipIf(onnxruntime is None, 'ONNX Runtime unavailable')
class ONNXExporterTester(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(123)

    def run_model(self, model, inputs_list, tolerate_small_mismatch=False,
                  do_constant_folding=True, dynamic_axes=None,
                  output_names=None, input_names=None):
        model.eval()

        onnx_io = io.BytesIO()
        # export to onnx with the first input
        torch.onnx.export(
            model,
            inputs_list[0],
            onnx_io,
            do_constant_folding=do_constant_folding,
            opset_version=_onnx_opset_version,
            dynamic_axes=dynamic_axes,
            input_names=input_names,
            output_names=output_names,
        )
        # validate the exported model with onnx runtime
        for test_inputs in inputs_list:
            with torch.no_grad():
                if isinstance(test_inputs, torch.Tensor) or isinstance(test_inputs, list):
                    test_inputs = (test_inputs,)
                test_ouputs = model(*test_inputs)
                if isinstance(test_ouputs, torch.Tensor):
                    test_ouputs = (test_ouputs,)
            self.ort_validate(onnx_io, test_inputs, test_ouputs, tolerate_small_mismatch)

    def ort_validate(self, onnx_io, inputs, outputs, tolerate_small_mismatch=False):

        inputs, _ = torch.jit._flatten(inputs)
        outputs, _ = torch.jit._flatten(outputs)

        def to_numpy(tensor):
            if tensor.requires_grad:
                return tensor.detach().cpu().numpy()
            else:
                return tensor.cpu().numpy()

        inputs = list(map(to_numpy, inputs))
        outputs = list(map(to_numpy, outputs))

        ort_session = onnxruntime.InferenceSession(onnx_io.getvalue())
        # compute onnxruntime output prediction
        ort_inputs = dict((ort_session.get_inputs()[i].name, inpt) for i, inpt in enumerate(inputs))
        ort_outs = ort_session.run(None, ort_inputs)

        for i in range(0, len(outputs)):
            try:
                torch.testing.assert_allclose(outputs[i], ort_outs[i], rtol=1e-03, atol=1e-05)
            except AssertionError as error:
                if tolerate_small_mismatch:
                    self.assertIn("(0.00%)", str(error), str(error))
                else:
                    raise

    def get_image_from_url(self, url, size=None):
        import requests
        from PIL import Image
        from io import BytesIO
        from torchvision import transforms

        data = requests.get(url)
        image = Image.open(BytesIO(data.content)).convert("RGB")

        if size is None:
            size = (300, 200)
        image = image.resize(size, Image.BILINEAR)

        to_tensor = transforms.ToTensor()
        return to_tensor(image)

    def get_test_images(self):
        image_url = "http://farm3.staticflickr.com/2469/3915380994_2e611b1779_z.jpg"
        image = self.get_image_from_url(url=image_url, size=(100, 320))

        image_url2 = "https://pytorch.org/tutorials/_static/img/tv_tutorial/tv_image05.png"
        image2 = self.get_image_from_url(url=image_url2, size=(250, 380))

        images_one = [image]
        images_two = [image2]
        return images_one, images_two

    def test_yolov5s_r31(self):
        images_one, images_two = self.get_test_images()
        images_dummy = [torch.ones(3, 100, 100) * 0.3]
        model = yolov5s(upstream_version='v3.1', export_friendly=True, pretrained=True)
        model.eval()
        model(images_one)
        # Test exported model on images of different size, or dummy input
        self.run_model(model, [(images_one,), (images_two,), (images_dummy,)], input_names=["images_tensors"],
                       output_names=["outputs"],
                       dynamic_axes={"images_tensors": [0, 1, 2], "outputs": [0, 1, 2]},
                       tolerate_small_mismatch=True)
        # Test exported model for an image with no detections on other images
        self.run_model(model, [(images_dummy,), (images_one,)], input_names=["images_tensors"],
                       output_names=["outputs"],
                       dynamic_axes={"images_tensors": [0, 1, 2], "outputs": [0, 1, 2]},
                       tolerate_small_mismatch=True)

    def test_yolov5m_r40(self):
        images_one, images_two = self.get_test_images()
        images_dummy = [torch.ones(3, 100, 100) * 0.3]
        model = yolov5m(upstream_version='v4.0', export_friendly=True, pretrained=True)
        model.eval()
        model(images_one)
        # Test exported model on images of different size, or dummy input
        self.run_model(model, [(images_one,), (images_two,), (images_dummy,)], input_names=["images_tensors"],
                       output_names=["outputs"],
                       dynamic_axes={"images_tensors": [0, 1, 2], "outputs": [0, 1, 2]},
                       tolerate_small_mismatch=True)
        # Test exported model for an image with no detections on other images
        self.run_model(model, [(images_dummy,), (images_one,)], input_names=["images_tensors"],
                       output_names=["outputs"],
                       dynamic_axes={"images_tensors": [0, 1, 2], "outputs": [0, 1, 2]},
                       tolerate_small_mismatch=True)

    def test_yolotr(self):
        images_one, images_two = self.get_test_images()
        images_dummy = [torch.ones(3, 100, 100) * 0.3]
        model = yolotr(upstream_version='v4.0', export_friendly=True, pretrained=True)
        model.eval()
        model(images_one)
        # Test exported model on images of different size, or dummy input
        self.run_model(model, [(images_one,), (images_two,), (images_dummy,)], input_names=["images_tensors"],
                       output_names=["outputs"],
                       dynamic_axes={"images_tensors": [0, 1, 2], "outputs": [0, 1, 2]},
                       tolerate_small_mismatch=True)
        # Test exported model for an image with no detections on other images
        self.run_model(model, [(images_dummy,), (images_one,)], input_names=["images_tensors"],
                       output_names=["outputs"],
                       dynamic_axes={"images_tensors": [0, 1, 2], "outputs": [0, 1, 2]},
                       tolerate_small_mismatch=True)


if __name__ == '__main__':
    unittest.main()

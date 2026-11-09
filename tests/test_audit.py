POSITIVE_ORACLE = ('image cropping', 'image-cropping', 'imagecropping', 'image crop', 'photo cropping', 'photo-cropping', 'picture cropping', 'crop images', 'crops images', 'cropping images', 'crop photos', 'crops photos', 'cropping photos', 'crop pictures', 'crops pictures', 'cropping pictures', 'crop an image', 'crops an image', 'cropping an image', 'crop the image', 'crops the image', 'cropping the image', 'crop images to', 'crop image to', 'crop images to a specific size', 'crop images to any size', 'image crop tool', 'image crop library', 'image crop feature', 'image crop support', 'supports image cropping', 'image cropping capability', 'image cropping pipeline', 'image cropping algorithm', 'image cropping software', 'image cropping app', 'image cropping model', 'automatic image cropping', 'automated image cropping', 'image cropper', 'image croppers', 'crop image dimensions', 'crop image region', 'crop a region', 'crop regions', 'cropping regions', 'center crop', 'center-crop', 'random crop', 'crop to size')
NEGATIVE_ORACLE = ('does not support image cropping', 'do not support image cropping', "doesn't support image cropping", "don't support image cropping", 'no image cropping', 'without image cropping', 'never performs image cropping', 'does not perform image cropping', 'image cropping not supported', 'image cropping unsupported', 'no image cropping support', 'lacks image cropping', 'missing image cropping', 'image cropping disabled', 'no image cropping capability', 'without image cropping support', 'does not provide image cropping', 'no image cropping model', 'image cropping not available', 'does not use image cropping', 'no image crop', 'without image crop', 'does not support image crop', 'no image cropping feature')
GENERIC_ORACLE = ('crop_image', 'crop_images', 'crop_photo', 'crop_photos', 'crop_picture', 'crop_pictures', 'crop_image_to', 'crop_to', 'crop_to_size', 'crop_image_dimensions', 'crop_image_width', 'crop_image_height', 'crop_center', 'crop_and_save', 'crop_image_file', 'create_crop', 'make_crop', 'generate_crop', 'crop_region', 'crop_area', 'extract_region', 'extract_crop', 'crop_thumbnail', 'center_crop')
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from image_cropping_claim_audit import phrases as p
from image_cropping_claim_audit.audit import audit, claims, module_evidence, prose
from image_cropping_claim_audit.__main__ import main


class AuditTests(unittest.TestCase):
    def fixture(self, readme='', code=None, test=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / 'README.md').write_text(readme)
        if code is not None:
            (root / 'app.py').write_text(code)
        if test is not None:
            (root / 'tests').mkdir()
            (root / 'tests/test_fixture.py').write_text(test)
        return root

    def cli(self, root, *options):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = main(['audit', str(root), *options])
        return result, output.getvalue(), errors.getvalue()

    def test_phrase_oracle(self):
        self.assertEqual(p.IMAGECROPPING, POSITIVE_ORACLE)
        self.assertEqual(p.NOIMAGECROPPING, NEGATIVE_ORACLE)

    def test_generic_oracle(self):
        self.assertEqual(p.GENERIC_NAMES, GENERIC_ORACLE)

    def test_route_lists(self):
        self.assertEqual(p.PIL_METHODS, ('crop',))
        self.assertEqual(p.PIL_OPS_CALL, ('PIL', 'ImageOps.crop'))
        self.assertEqual(p.CV_TRACE_CALL, 'cv2.imread')
        self.assertEqual(p.SKIMAGE_CALL, ('skimage.util', 'crop'))
        self.assertEqual(p.CROP_CLASSES, ('RandomCrop', 'CenterCrop', 'FiveCrop', 'TenCrop'))
        self.assertEqual(p.TRANSFORM_SOURCES, ('torchvision.transforms', 'torchvision.transforms.v2'))
        self.assertEqual(p.FUNCTIONAL_CALL, ('torchvision.transforms.functional', 'crop'))
        self.assertTrue(p.REQUIRES_INSTANCE_CALL)

    def test_span_removal(self):
        self.assertEqual(claims('does not support image cropping'), ([], ['does not support image cropping']))
        self.assertEqual(audit(self.fixture('does not support image cropping')), [])

    def test_longest_model(self):
        self.assertEqual(claims('image cropping model')[0], ['image cropping model'])

    def test_longest_size(self):
        self.assertEqual(claims('crop images to any size')[0], ['crop images to any size'])

    def test_case(self):
        self.assertEqual(audit(self.fixture('IMAGE CROPPING'))[0]['verdict'], 'HIGH')

    def test_agricultural_collision(self):
        self.assertEqual(claims('we crop images of wheat fields from satellites')[0], ['crop images'])

    def test_augmentation_collision(self):
        self.assertEqual(claims('we use center crop in the training pipeline')[0], ['center crop'])

    def test_no_hyphen_normalization(self):
        self.assertEqual(claims('crop-images'), ([], []))

    def test_fenced(self):
        self.assertEqual(audit(self.fixture('```text\nimage cropping\n```')), [])

    def test_inline(self):
        self.assertEqual(audit(self.fixture('`image cropping`'))[0]['verdict'], 'HIGH')

    def test_split_modules(self):
        root = self.fixture('image cropping', 'from PIL import Image\nim = Image.open("x")')
        (root / 'other.py').write_text('im.crop((0,0,1,1))')
        self.assertEqual(audit(root)[0]['verdict'], 'HIGH')

    def test_cli_good(self):
        self.assertEqual(self.cli(self.fixture('image cropping', 'x.crop_image()'))[:2], (0, 'PASS\n'))

    def test_cli_bad(self):
        code, out, _ = self.cli(self.fixture('image cropping'))
        self.assertEqual(code, 2)
        self.assertIn('HIGH documented-image-cropping-claim-false', out)

    def test_cli_test_only(self):
        root = self.fixture(test='"image cropping"')
        self.assertEqual(self.cli(root)[0], 0)
        self.assertIn('MEDIUM', self.cli(root)[1])
        self.assertEqual(self.cli(root, '--fail-on', 'medium')[0], 2)

    def test_cli_denial(self):
        result = self.cli(self.fixture('no image cropping', 'x.crop_image()'))
        self.assertEqual(result[0], 2)
        self.assertIn('HIGH documented-no-image-cropping-claim-false', result[1])

    def test_cli_no_claim(self):
        self.assertEqual(self.cli(self.fixture('Hello'))[:2], (0, 'PASS\n'))

    def test_cli_json(self):
        code, out, _ = self.cli(self.fixture('image cropping'), '--json', '--verbose')
        self.assertEqual(code, 2)
        finding = json.loads(out)[0]
        self.assertEqual(finding['verdict'], 'HIGH')
        self.assertTrue(finding['message'])

    def test_cli_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            main(['--version'])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(out.getvalue(), '0.1.0\n')

    def test_cli_ignore(self):
        root = self.fixture('image cropping', 'x.crop_image()')
        self.assertEqual(self.cli(root, '--ignore', 'app')[0], 2)
        root = self.fixture('image cropping')
        self.assertEqual(self.cli(root, '--ignore', 'README')[0], 0)

    def test_cli_ignore_before_positional(self):
        root = self.fixture('image cropping')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['audit', '--ignore', 'README', str(root)]), 0)

    def test_cli_errors(self):
        self.assertEqual(self.cli('/nonexistent/path')[0], 1)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(['audit', '--fail-on', 'invalid'])
        self.assertEqual(raised.exception.code, 1)

    def test_readme_self_audit(self):
        readme = (Path(__file__).resolve().parents[1] / 'README.md').read_text()
        self.assertEqual(self.cli(self.fixture(readme))[:2], (0, 'PASS\n'))

    def test_scope(self):
        root = self.fixture('')
        (root / 'docs').mkdir()
        (root / 'docs/guide.md').write_text('image cropping')
        self.assertEqual(audit(root)[0]['verdict'], 'HIGH')
        self.assertEqual(audit(root, ['docs']), [])
        (root / '.venv').mkdir()
        (root / '.venv/hidden.py').write_text('x.crop_image()')
        self.assertEqual(audit(root)[0]['verdict'], 'HIGH')

    def test_positive_000(self):
        self.assertTrue(module_evidence('from PIL import Image\nim=Image.open("x")\nim.crop((0,0,1,1))'))

    def test_positive_001(self):
        self.assertTrue(module_evidence('from PIL import Image\nImage.open("x").crop((0,0,1,1))'))

    def test_positive_002(self):
        self.assertTrue(module_evidence('import PIL\nPIL.Image.open("x").crop((0,0,1,1))'))

    def test_positive_003(self):
        self.assertTrue(module_evidence('from PIL import Image as I\nim=I.open("x")\nim.crop((0,0,1,1))'))

    def test_positive_004(self):
        self.assertTrue(module_evidence('from PIL import ImageOps\nImageOps.crop(im, 2)'))

    def test_positive_005(self):
        self.assertTrue(module_evidence('from PIL import ImageOps as O\nO.crop(im,2)'))

    def test_positive_006(self):
        self.assertTrue(module_evidence('import PIL\nPIL.ImageOps.crop(im,2)'))

    def test_positive_007(self):
        self.assertTrue(module_evidence('import cv2\nim=cv2.imread("x")\nim[1:4, 2:5]'))

    def test_positive_008(self):
        self.assertTrue(module_evidence('import cv2\nim=cv2.imread("x")\nim[:100, :100]'))

    def test_positive_009(self):
        self.assertTrue(module_evidence('import cv2\nim=cv2.imread("x")\nim[10:20]'))

    def test_positive_010(self):
        self.assertTrue(module_evidence('import cv2 as c\nim=c.imread("x")\nim[1:4, 2:5]'))

    def test_positive_011(self):
        self.assertTrue(module_evidence('import cv2 as c\nim=c.imread("x")\nim[:100, :100]'))

    def test_positive_012(self):
        self.assertTrue(module_evidence('import cv2 as c\nim=c.imread("x")\nim[10:20]'))

    def test_positive_013(self):
        self.assertTrue(module_evidence('import skimage.util\nskimage.util.crop(im, 1, 2)'))

    def test_positive_014(self):
        self.assertTrue(module_evidence('import skimage.util as u\nu.crop(im, 1, 2)'))

    def test_positive_015(self):
        self.assertTrue(module_evidence('from skimage import util\nutil.crop(im, 1, 2)'))

    def test_positive_016(self):
        self.assertTrue(module_evidence('from skimage.util import crop\ncrop(im, 1, 2)'))

    def test_positive_017(self):
        self.assertTrue(module_evidence('from skimage.util import crop as c\nc(im, 1, 2)'))

    def test_positive_018(self):
        self.assertTrue(module_evidence('import torchvision.transforms.functional\ntorchvision.transforms.functional.crop(im, 1, 2)'))

    def test_positive_019(self):
        self.assertTrue(module_evidence('import torchvision.transforms.functional as F\nF.crop(im, 1, 2)'))

    def test_positive_020(self):
        self.assertTrue(module_evidence('from torchvision.transforms import functional\nfunctional.crop(im, 1, 2)'))

    def test_positive_021(self):
        self.assertTrue(module_evidence('from torchvision.transforms.functional import crop\ncrop(im, 1, 2)'))

    def test_positive_022(self):
        self.assertTrue(module_evidence('from torchvision.transforms.functional import crop as c\nc(im, 1, 2)'))

    def test_positive_023(self):
        self.assertTrue(module_evidence('from torchvision.transforms import RandomCrop\nt=RandomCrop(10)\nt(im)'))

    def test_positive_024(self):
        self.assertTrue(module_evidence('from torchvision.transforms.v2 import RandomCrop\nt=RandomCrop(10)\nt(im)'))

    def test_positive_025(self):
        self.assertTrue(module_evidence('from torchvision.transforms import RandomCrop as C\nt=C(10)\nt(im)'))

    def test_positive_026(self):
        self.assertTrue(module_evidence('import torchvision.transforms\nt=torchvision.transforms.RandomCrop(10)\nt(im)'))

    def test_positive_027(self):
        self.assertTrue(module_evidence('from torchvision import transforms\nt=transforms.RandomCrop(10)\nt(im)'))

    def test_positive_028(self):
        self.assertTrue(module_evidence('import torchvision.transforms.v2\nt=torchvision.transforms.v2.RandomCrop(10)\nt(im)'))

    def test_positive_029(self):
        self.assertTrue(module_evidence('from torchvision.transforms import CenterCrop\nt=CenterCrop(10)\nt(im)'))

    def test_positive_030(self):
        self.assertTrue(module_evidence('from torchvision.transforms.v2 import CenterCrop\nt=CenterCrop(10)\nt(im)'))

    def test_positive_031(self):
        self.assertTrue(module_evidence('from torchvision.transforms import CenterCrop as C\nt=C(10)\nt(im)'))

    def test_positive_032(self):
        self.assertTrue(module_evidence('import torchvision.transforms\nt=torchvision.transforms.CenterCrop(10)\nt(im)'))

    def test_positive_033(self):
        self.assertTrue(module_evidence('from torchvision import transforms\nt=transforms.CenterCrop(10)\nt(im)'))

    def test_positive_034(self):
        self.assertTrue(module_evidence('import torchvision.transforms.v2\nt=torchvision.transforms.v2.CenterCrop(10)\nt(im)'))

    def test_positive_035(self):
        self.assertTrue(module_evidence('from torchvision.transforms import FiveCrop\nt=FiveCrop(10)\nt(im)'))

    def test_positive_036(self):
        self.assertTrue(module_evidence('from torchvision.transforms.v2 import FiveCrop\nt=FiveCrop(10)\nt(im)'))

    def test_positive_037(self):
        self.assertTrue(module_evidence('from torchvision.transforms import FiveCrop as C\nt=C(10)\nt(im)'))

    def test_positive_038(self):
        self.assertTrue(module_evidence('import torchvision.transforms\nt=torchvision.transforms.FiveCrop(10)\nt(im)'))

    def test_positive_039(self):
        self.assertTrue(module_evidence('from torchvision import transforms\nt=transforms.FiveCrop(10)\nt(im)'))

    def test_positive_040(self):
        self.assertTrue(module_evidence('import torchvision.transforms.v2\nt=torchvision.transforms.v2.FiveCrop(10)\nt(im)'))

    def test_positive_041(self):
        self.assertTrue(module_evidence('from torchvision.transforms import TenCrop\nt=TenCrop(10)\nt(im)'))

    def test_positive_042(self):
        self.assertTrue(module_evidence('from torchvision.transforms.v2 import TenCrop\nt=TenCrop(10)\nt(im)'))

    def test_positive_043(self):
        self.assertTrue(module_evidence('from torchvision.transforms import TenCrop as C\nt=C(10)\nt(im)'))

    def test_positive_044(self):
        self.assertTrue(module_evidence('import torchvision.transforms\nt=torchvision.transforms.TenCrop(10)\nt(im)'))

    def test_positive_045(self):
        self.assertTrue(module_evidence('from torchvision import transforms\nt=transforms.TenCrop(10)\nt(im)'))

    def test_positive_046(self):
        self.assertTrue(module_evidence('import torchvision.transforms.v2\nt=torchvision.transforms.v2.TenCrop(10)\nt(im)'))

    def test_positive_047(self):
        self.assertTrue(module_evidence('x.crop_image(im)'))

    def test_positive_048(self):
        self.assertTrue(module_evidence('from tool import crop_image\ncrop_image(im)'))

    def test_positive_049(self):
        self.assertTrue(module_evidence('from tool import crop_image as c\nc(im)'))

    def test_positive_050(self):
        self.assertTrue(module_evidence('x.crop_images(im)'))

    def test_positive_051(self):
        self.assertTrue(module_evidence('from tool import crop_images\ncrop_images(im)'))

    def test_positive_052(self):
        self.assertTrue(module_evidence('from tool import crop_images as c\nc(im)'))

    def test_positive_053(self):
        self.assertTrue(module_evidence('x.crop_photo(im)'))

    def test_positive_054(self):
        self.assertTrue(module_evidence('from tool import crop_photo\ncrop_photo(im)'))

    def test_positive_055(self):
        self.assertTrue(module_evidence('from tool import crop_photo as c\nc(im)'))

    def test_positive_056(self):
        self.assertTrue(module_evidence('x.crop_photos(im)'))

    def test_positive_057(self):
        self.assertTrue(module_evidence('from tool import crop_photos\ncrop_photos(im)'))

    def test_positive_058(self):
        self.assertTrue(module_evidence('from tool import crop_photos as c\nc(im)'))

    def test_positive_059(self):
        self.assertTrue(module_evidence('x.crop_picture(im)'))

    def test_positive_060(self):
        self.assertTrue(module_evidence('from tool import crop_picture\ncrop_picture(im)'))

    def test_positive_061(self):
        self.assertTrue(module_evidence('from tool import crop_picture as c\nc(im)'))

    def test_positive_062(self):
        self.assertTrue(module_evidence('x.crop_pictures(im)'))

    def test_positive_063(self):
        self.assertTrue(module_evidence('from tool import crop_pictures\ncrop_pictures(im)'))

    def test_positive_064(self):
        self.assertTrue(module_evidence('from tool import crop_pictures as c\nc(im)'))

    def test_positive_065(self):
        self.assertTrue(module_evidence('x.crop_image_to(im)'))

    def test_positive_066(self):
        self.assertTrue(module_evidence('from tool import crop_image_to\ncrop_image_to(im)'))

    def test_positive_067(self):
        self.assertTrue(module_evidence('from tool import crop_image_to as c\nc(im)'))

    def test_positive_068(self):
        self.assertTrue(module_evidence('x.crop_to(im)'))

    def test_positive_069(self):
        self.assertTrue(module_evidence('from tool import crop_to\ncrop_to(im)'))

    def test_positive_070(self):
        self.assertTrue(module_evidence('from tool import crop_to as c\nc(im)'))

    def test_positive_071(self):
        self.assertTrue(module_evidence('x.crop_to_size(im)'))

    def test_positive_072(self):
        self.assertTrue(module_evidence('from tool import crop_to_size\ncrop_to_size(im)'))

    def test_positive_073(self):
        self.assertTrue(module_evidence('from tool import crop_to_size as c\nc(im)'))

    def test_positive_074(self):
        self.assertTrue(module_evidence('x.crop_image_dimensions(im)'))

    def test_positive_075(self):
        self.assertTrue(module_evidence('from tool import crop_image_dimensions\ncrop_image_dimensions(im)'))

    def test_positive_076(self):
        self.assertTrue(module_evidence('from tool import crop_image_dimensions as c\nc(im)'))

    def test_positive_077(self):
        self.assertTrue(module_evidence('x.crop_image_width(im)'))

    def test_positive_078(self):
        self.assertTrue(module_evidence('from tool import crop_image_width\ncrop_image_width(im)'))

    def test_positive_079(self):
        self.assertTrue(module_evidence('from tool import crop_image_width as c\nc(im)'))

    def test_positive_080(self):
        self.assertTrue(module_evidence('x.crop_image_height(im)'))

    def test_positive_081(self):
        self.assertTrue(module_evidence('from tool import crop_image_height\ncrop_image_height(im)'))

    def test_positive_082(self):
        self.assertTrue(module_evidence('from tool import crop_image_height as c\nc(im)'))

    def test_positive_083(self):
        self.assertTrue(module_evidence('x.crop_center(im)'))

    def test_positive_084(self):
        self.assertTrue(module_evidence('from tool import crop_center\ncrop_center(im)'))

    def test_positive_085(self):
        self.assertTrue(module_evidence('from tool import crop_center as c\nc(im)'))

    def test_positive_086(self):
        self.assertTrue(module_evidence('x.crop_and_save(im)'))

    def test_positive_087(self):
        self.assertTrue(module_evidence('from tool import crop_and_save\ncrop_and_save(im)'))

    def test_positive_088(self):
        self.assertTrue(module_evidence('from tool import crop_and_save as c\nc(im)'))

    def test_positive_089(self):
        self.assertTrue(module_evidence('x.crop_image_file(im)'))

    def test_positive_090(self):
        self.assertTrue(module_evidence('from tool import crop_image_file\ncrop_image_file(im)'))

    def test_positive_091(self):
        self.assertTrue(module_evidence('from tool import crop_image_file as c\nc(im)'))

    def test_positive_092(self):
        self.assertTrue(module_evidence('x.create_crop(im)'))

    def test_positive_093(self):
        self.assertTrue(module_evidence('from tool import create_crop\ncreate_crop(im)'))

    def test_positive_094(self):
        self.assertTrue(module_evidence('from tool import create_crop as c\nc(im)'))

    def test_positive_095(self):
        self.assertTrue(module_evidence('x.make_crop(im)'))

    def test_positive_096(self):
        self.assertTrue(module_evidence('from tool import make_crop\nmake_crop(im)'))

    def test_positive_097(self):
        self.assertTrue(module_evidence('from tool import make_crop as c\nc(im)'))

    def test_positive_098(self):
        self.assertTrue(module_evidence('x.generate_crop(im)'))

    def test_positive_099(self):
        self.assertTrue(module_evidence('from tool import generate_crop\ngenerate_crop(im)'))

    def test_positive_100(self):
        self.assertTrue(module_evidence('from tool import generate_crop as c\nc(im)'))

    def test_positive_101(self):
        self.assertTrue(module_evidence('x.crop_region(im)'))

    def test_positive_102(self):
        self.assertTrue(module_evidence('from tool import crop_region\ncrop_region(im)'))

    def test_positive_103(self):
        self.assertTrue(module_evidence('from tool import crop_region as c\nc(im)'))

    def test_positive_104(self):
        self.assertTrue(module_evidence('x.crop_area(im)'))

    def test_positive_105(self):
        self.assertTrue(module_evidence('from tool import crop_area\ncrop_area(im)'))

    def test_positive_106(self):
        self.assertTrue(module_evidence('from tool import crop_area as c\nc(im)'))

    def test_positive_107(self):
        self.assertTrue(module_evidence('x.extract_region(im)'))

    def test_positive_108(self):
        self.assertTrue(module_evidence('from tool import extract_region\nextract_region(im)'))

    def test_positive_109(self):
        self.assertTrue(module_evidence('from tool import extract_region as c\nc(im)'))

    def test_positive_110(self):
        self.assertTrue(module_evidence('x.extract_crop(im)'))

    def test_positive_111(self):
        self.assertTrue(module_evidence('from tool import extract_crop\nextract_crop(im)'))

    def test_positive_112(self):
        self.assertTrue(module_evidence('from tool import extract_crop as c\nc(im)'))

    def test_positive_113(self):
        self.assertTrue(module_evidence('x.crop_thumbnail(im)'))

    def test_positive_114(self):
        self.assertTrue(module_evidence('from tool import crop_thumbnail\ncrop_thumbnail(im)'))

    def test_positive_115(self):
        self.assertTrue(module_evidence('from tool import crop_thumbnail as c\nc(im)'))

    def test_positive_116(self):
        self.assertTrue(module_evidence('x.center_crop(im)'))

    def test_positive_117(self):
        self.assertTrue(module_evidence('from tool import center_crop\ncenter_crop(im)'))

    def test_positive_118(self):
        self.assertTrue(module_evidence('from tool import center_crop as c\nc(im)'))

    def test_rejection_000(self):
        self.assertFalse(module_evidence('import PIL\nimport cv2\nimport skimage.util\nimport torchvision.transforms'))

    def test_rejection_001(self):
        self.assertFalse(module_evidence('from PIL import Image\nImage.open("x")'))

    def test_rejection_002(self):
        self.assertFalse(module_evidence('im.crop((0,0,1,1))'))

    def test_rejection_003(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")'))

    def test_rejection_004(self):
        self.assertFalse(module_evidence('im[1:4,2:5]'))

    def test_rejection_005(self):
        self.assertFalse(module_evidence('other.crop(im)'))

    def test_rejection_006(self):
        self.assertFalse(module_evidence('crop(im)'))

    def test_rejection_007(self):
        self.assertFalse(module_evidence('from PIL import ImageOps\nImageOps.fit(im, (10,10))'))

    def test_rejection_008(self):
        self.assertFalse(module_evidence('from PIL import Image\nim=Image.open("x")\nim.resize((10,10))\nim.thumbnail((10,10))\nim.rotate(90)\nim.transpose(1)'))

    def test_rejection_009(self):
        self.assertFalse(module_evidence('import cv2\ncv2.resize(im,(10,10))\ncv2.flip(im,1)\ncv2.rotate(im,1)'))

    def test_rejection_010(self):
        self.assertFalse(module_evidence('remove_background(im)'))

    def test_rejection_011(self):
        self.assertFalse(module_evidence('detector.detect(im)'))

    def test_rejection_012(self):
        self.assertFalse(module_evidence('model.upscale(im)'))

    def test_rejection_013(self):
        self.assertFalse(module_evidence('model.classify(im)'))

    def test_rejection_014(self):
        self.assertFalse(module_evidence('model.caption(im)'))

    def test_rejection_015(self):
        self.assertFalse(module_evidence('model.generate(im)'))

    def test_rejection_016(self):
        self.assertFalse(module_evidence('model.inpaint(im)'))

    def test_rejection_017(self):
        self.assertFalse(module_evidence('model.colorize(im)'))

    def test_rejection_018(self):
        self.assertFalse(module_evidence('model.stitch(im)'))

    def test_rejection_019(self):
        self.assertFalse(module_evidence('"crop cropping"\n# crop_image(im)\n'))

    def test_rejection_020(self):
        self.assertFalse(module_evidence('from tool import crop_image\ncrop_image'))

    def test_rejection_021(self):
        self.assertFalse(module_evidence('import subprocess\nsubprocess.run(["crop", "x"])'))

    def test_rejection_022(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")\nim[::-1]'))

    def test_rejection_023(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")\nim[::2]'))

    def test_rejection_024(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")\nim[0]'))

    def test_rejection_025(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")\nim[:, :, 1:4]'))

    def test_rejection_026(self):
        self.assertFalse(module_evidence('RandomCrop(10)'))

    def test_rejection_027(self):
        self.assertFalse(module_evidence('other.RandomCrop(10)'))

    def test_rejection_028(self):
        self.assertFalse(module_evidence('from torchvision.transforms import RandomCrop\nt=RandomCrop(10)'))

    def test_rejection_029(self):
        self.assertFalse(module_evidence('t(im)'))

    def test_rejection_030(self):
        self.assertFalse(module_evidence('CenterCrop(10)'))

    def test_rejection_031(self):
        self.assertFalse(module_evidence('other.CenterCrop(10)'))

    def test_rejection_032(self):
        self.assertFalse(module_evidence('from torchvision.transforms import CenterCrop\nt=CenterCrop(10)'))

    def test_rejection_033(self):
        self.assertFalse(module_evidence('t(im)'))

    def test_rejection_034(self):
        self.assertFalse(module_evidence('FiveCrop(10)'))

    def test_rejection_035(self):
        self.assertFalse(module_evidence('other.FiveCrop(10)'))

    def test_rejection_036(self):
        self.assertFalse(module_evidence('from torchvision.transforms import FiveCrop\nt=FiveCrop(10)'))

    def test_rejection_037(self):
        self.assertFalse(module_evidence('t(im)'))

    def test_rejection_038(self):
        self.assertFalse(module_evidence('TenCrop(10)'))

    def test_rejection_039(self):
        self.assertFalse(module_evidence('other.TenCrop(10)'))

    def test_rejection_040(self):
        self.assertFalse(module_evidence('from torchvision.transforms import TenCrop\nt=TenCrop(10)'))

    def test_rejection_041(self):
        self.assertFalse(module_evidence('t(im)'))

    def test_shadow_000_function(self):
        self.assertFalse(module_evidence('from PIL import Image\nim=Image.open("x")\nim.crop((0,0,1,1))\ndef Image(*args): pass'))

    def test_shadow_000_class(self):
        self.assertFalse(module_evidence('from PIL import Image\nim=Image.open("x")\nim.crop((0,0,1,1))\nclass Image: pass'))

    def test_shadow_001_function(self):
        self.assertFalse(module_evidence('from PIL import ImageOps\nImageOps.crop(im, 2)\ndef ImageOps(*args): pass'))

    def test_shadow_001_class(self):
        self.assertFalse(module_evidence('from PIL import ImageOps\nImageOps.crop(im, 2)\nclass ImageOps: pass'))

    def test_shadow_002_function(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")\nim[1:4]\ndef cv2(*args): pass'))

    def test_shadow_002_class(self):
        self.assertFalse(module_evidence('import cv2\nim=cv2.imread("x")\nim[1:4]\nclass cv2: pass'))

    def test_shadow_003_function(self):
        self.assertFalse(module_evidence('from skimage.util import crop\ncrop(im, 1)\ndef crop(*args): pass'))

    def test_shadow_003_class(self):
        self.assertFalse(module_evidence('from skimage.util import crop\ncrop(im, 1)\nclass crop: pass'))

    def test_shadow_004_function(self):
        self.assertFalse(module_evidence('from torchvision.transforms.functional import crop\ncrop(im,1)\ndef crop(*args): pass'))

    def test_shadow_004_class(self):
        self.assertFalse(module_evidence('from torchvision.transforms.functional import crop\ncrop(im,1)\nclass crop: pass'))

    def test_shadow_005_function(self):
        self.assertFalse(module_evidence('from tool import crop_image\ncrop_image(im)\ndef crop_image(*args): pass'))

    def test_shadow_005_class(self):
        self.assertFalse(module_evidence('from tool import crop_image\ncrop_image(im)\nclass crop_image: pass'))

    def test_shadow_006_function(self):
        self.assertFalse(module_evidence('from torchvision.transforms import RandomCrop\nt=RandomCrop(10)\nt(im)\ndef RandomCrop(*args): pass'))

    def test_shadow_006_class(self):
        self.assertFalse(module_evidence('from torchvision.transforms import RandomCrop\nt=RandomCrop(10)\nt(im)\nclass RandomCrop: pass'))

    def test_shadow_007_function(self):
        self.assertFalse(module_evidence('from torchvision.transforms import CenterCrop\nt=CenterCrop(10)\nt(im)\ndef CenterCrop(*args): pass'))

    def test_shadow_007_class(self):
        self.assertFalse(module_evidence('from torchvision.transforms import CenterCrop\nt=CenterCrop(10)\nt(im)\nclass CenterCrop: pass'))

    def test_shadow_008_function(self):
        self.assertFalse(module_evidence('from torchvision.transforms import FiveCrop\nt=FiveCrop(10)\nt(im)\ndef FiveCrop(*args): pass'))

    def test_shadow_008_class(self):
        self.assertFalse(module_evidence('from torchvision.transforms import FiveCrop\nt=FiveCrop(10)\nt(im)\nclass FiveCrop: pass'))

    def test_shadow_009_function(self):
        self.assertFalse(module_evidence('from torchvision.transforms import TenCrop\nt=TenCrop(10)\nt(im)\ndef TenCrop(*args): pass'))

    def test_shadow_009_class(self):
        self.assertFalse(module_evidence('from torchvision.transforms import TenCrop\nt=TenCrop(10)\nt(im)\nclass TenCrop: pass'))

    def test_all_positive_phrases_match(self):
        for phrase in POSITIVE_ORACLE:
            with self.subTest(phrase=phrase):
                self.assertEqual(claims(phrase.upper())[0], [phrase])

    def test_all_denial_phrases_remove_positive_spans(self):
        for phrase in NEGATIVE_ORACLE:
            with self.subTest(phrase=phrase):
                self.assertEqual(claims(phrase.upper()), ([], [phrase]))

    def test_two_families(self):
        root = self.fixture('image cropping; no image cropping', 'x.crop_image()')
        self.assertEqual([f['rule'] for f in audit(root)], ['documented-no-image-cropping-claim-false'])

    def test_family_collapse(self):
        self.assertEqual(len(audit(self.fixture('image cropping; crop photos; crop images'))), 1)

    def test_pil_crop_shadow(self):
        self.assertFalse(module_evidence('from PIL import Image\nim=Image.open("x")\nim.crop((0,0,1,1))\ndef crop(): pass'))

    def test_alias_shadow(self):
        self.assertFalse(module_evidence('from PIL import Image as I\nI.open("x").crop((0,0,1,1))\nclass I: pass'))

    def test_functional_base_shadow(self):
        self.assertFalse(module_evidence('from torchvision.transforms import functional\nfunctional.crop(im,1)\nclass functional: pass'))

    def test_generic_attribute_shadow(self):
        self.assertFalse(module_evidence('x.crop_image(im)\ndef crop_image(): pass'))

    def test_cv_split(self):
        root = self.fixture('image cropping', 'import cv2\nim=cv2.imread("x")')
        (root / 'other.py').write_text('im[1:4,2:5]')
        self.assertEqual(audit(root)[0]['verdict'], 'HIGH')

    def test_transform_split(self):
        root = self.fixture('image cropping', 'from torchvision.transforms import RandomCrop\nt=RandomCrop(10)')
        (root / 'other.py').write_text('t(im)')
        self.assertEqual(audit(root)[0]['verdict'], 'HIGH')

    def test_evidence_any_module(self):
        root = self.fixture('image cropping')
        (root / 'other.py').write_text('x.crop_image(im)')
        self.assertEqual(audit(root), [])

    def test_cli_verbose(self):
        code, out, err = self.cli(self.fixture('Hello', 'x=1'), '--verbose')
        self.assertEqual(code, 0)
        self.assertIn('Scope:', err)
        self.assertIn('app.py: no evidence', err)
        self.assertIn('README.md: documentation scanned', err)

    def test_repeat_ignore(self):
        root = self.fixture('image cropping')
        (root / 'docs').mkdir()
        (root / 'docs/a.md').write_text('image cropping')
        self.assertEqual(self.cli(root, '--ignore', 'README', '--ignore', 'docs')[0], 0)

    def test_no_claim_with_evidence(self):
        self.assertEqual(audit(self.fixture('Hello', 'x.crop_image()')), [])

    def test_denial_no_source(self):
        self.assertEqual(self.cli(self.fixture('no image cropping'))[:2], (0, 'PASS\n'))

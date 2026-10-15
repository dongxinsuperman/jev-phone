"""Annotation must preserve device geometry while placing readable point labels."""
import copy
import io
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
from jev_phone.core import annotate


def overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


class AnnotationContract(unittest.TestCase):
    def inspect_render(self, size, bounds):
        original_draw = ImageDraw.Draw
        labels, points = [], []
        class Recorder:
            def __init__(self, *args, **kwargs):
                self.draw = original_draw(*args, **kwargs)
            def __getattr__(self, name):
                return getattr(self.draw, name)
            def rectangle(self, xy, **kwargs):
                if kwargs.get('fill') == 'white':
                    labels.append(tuple(xy))
                return self.draw.rectangle(xy, **kwargs)
            def ellipse(self, xy, **kwargs):
                points.append(((xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2))
                return self.draw.ellipse(xy, **kwargs)
        source = io.BytesIO()
        Image.new('RGB', size, 'white').save(source, 'JPEG')
        nodes = [{'id': f'N{i+1}', 'bounds': box} for i, box in enumerate(bounds)]
        before = copy.deepcopy(nodes)
        with patch('jev_phone.core.ImageDraw.Draw', Recorder):
            output = annotate(source.getvalue(), nodes)
        self.assertEqual(nodes, before)
        self.assertEqual(points, [((b[0]+b[2])//2, (b[1]+b[3])//2) for b in bounds])
        self.assertEqual(len(labels), len(nodes))
        with Image.open(io.BytesIO(output)) as rendered:
            self.assertEqual(rendered.format, 'JPEG')
        return labels, points

    def test_overlapping_regions_keep_original_click_centers(self):
        self.inspect_render((512, 1024), [[4, 6, 31, 55], [0, 0, 512, 1024], [200, 400, 300, 600]])

    def test_edge_labels_stay_inside_image_without_covering_click_points(self):
        size = (512, 1024)
        labels, points = self.inspect_render(size, [[0,0,40,40], [472,0,512,40], [0,984,40,1024], [472,984,512,1024]])
        for left, top, right, bottom in labels:
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(top, 0)
            self.assertLessEqual(right, size[0])
            self.assertLessEqual(bottom, size[1])
            for x, y in points:
                self.assertFalse(left <= x <= right and top <= y <= bottom)

    def test_shared_centers_do_not_overwrite_other_candidate_labels(self):
        labels, _ = self.inspect_render((512, 1024), [[0,0,512,1024], [0,0,512,1024], [180,400,332,624]])
        for i, label in enumerate(labels):
            for other in labels[i+1:]:
                self.assertFalse(overlaps(label, other))


if __name__ == '__main__':
    unittest.main()

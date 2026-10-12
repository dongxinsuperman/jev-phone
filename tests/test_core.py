import unittest
from jev_phone.core import split_steps, candidates_from_tree

class InputContract(unittest.TestCase):
    def test_order_and_description_punctuation(self):
        self.assertEqual(split_steps("点击星球，点击我的；\n点击头像。"), ["点击星球", "点击我的", "点击头像"])

    def test_fixed_common_separators(self):
        self.assertEqual(split_steps("点击蓝点,唤醒提交，并点击继续推进到下一步"),
                         ["点击蓝点", "唤醒提交", "并点击继续推进到下一步"])
        self.assertEqual(split_steps("点击A!点击B？点击C.点击D；；"), ["点击A", "点击B", "点击C", "点击D"])

    def test_empty_and_limits(self):
        for text in ["；\n", ";".join(["点击"]*21), "点"*501]:
            with self.assertRaises(ValueError): split_steps(text)

    def test_clipping_and_hidden_nodes(self):
        xml='<hierarchy><node clickable="true" enabled="true" bounds="[-10,0][50,60]"/><node clickable="true" enabled="true" visible-to-user="false" bounds="[0,0][90,90]"/><node clickable="true" enabled="true" bounds="[120,0][150,10]"/></hierarchy>'
        nodes=candidates_from_tree(xml,100,100)
        self.assertEqual(len(nodes),1)
        self.assertEqual(nodes[0]["bounds"],[0,0,50,60])

if __name__=='__main__': unittest.main()

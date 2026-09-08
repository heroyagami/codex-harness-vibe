import ast
import unittest
from pathlib import Path


class PipelineOrchestrationTests(unittest.TestCase):
    def test_visual_critic_loop_belongs_to_run_scene(self):
        source = (Path(__file__).parents[1] / "src" / "legal_auto_motion" / "pipeline.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        functions = {node.name: node for node in module.body if isinstance(node, ast.FunctionDef)}
        run_calls = {node.func.id for node in ast.walk(functions["run_scene"]) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        memory_calls = {node.func.id for node in ast.walk(functions["_remember_critique"]) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertIn("_creative_critique", run_calls)
        self.assertIn("_verify_authored_scene", run_calls)
        self.assertNotIn("_creative_critique", memory_calls)
        self.assertTrue(any(isinstance(node, ast.Return) and node.value is not None for node in ast.walk(functions["run_scene"])))


if __name__ == "__main__":
    unittest.main()

from typing import Dict
import os


class PromptService:
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.prompts_dir = os.path.join(os.path.dirname(current_dir), "prompts")
        else:
            self.prompts_dir = prompts_dir
        
        self._cache = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        if prompt_name in self._cache:
            return self._cache[prompt_name]
        
        prompt_file = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        
        if not os.path.exists(prompt_file):
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        self._cache[prompt_name] = prompt_template
        return prompt_template
    
    def fill_prompt(self, prompt_name: str, **kwargs) -> str:
        template = self.load_prompt(prompt_name)
        return template.format(**kwargs)
    
    def get_prompt(self, prompt_name: str, **kwargs) -> str:
        return self.fill_prompt(prompt_name, **kwargs)
    
    def clear_cache(self):
        self._cache = {}


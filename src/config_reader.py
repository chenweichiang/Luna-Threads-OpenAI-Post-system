import yaml
import json
import re
from pathlib import Path

class PromptConfigReader:
    def __init__(self, prompt_file_path="prompt.md"):
        self.prompt_file_path = Path(prompt_file_path)
        self.config = self._read_prompt_file()
        
    def _read_prompt_file(self):
        """讀取並解析 prompt.md 文件"""
        if not self.prompt_file_path.exists():
            raise FileNotFoundError(f"找不到 {self.prompt_file_path}")
            
        with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 解析各個部分
        sections = {}
        current_section = None
        current_content = []
        json_content = ""
        in_json = False
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = self._process_section_content('\n'.join(current_content))
                current_section = line[3:].split(' (')[0]  # 移除括號中的英文
                current_content = []
            elif line.startswith('```json'):
                in_json = True
                json_content = ""
            elif line.startswith('```') and in_json:
                in_json = False
                if json_content:
                    try:
                        current_content.append(json.loads(json_content))
                    except json.JSONDecodeError:
                        current_content.append(json_content)
            elif in_json:
                json_content += line + '\n'
            else:
                current_content.append(line)
                
        if current_section:
            sections[current_section] = self._process_section_content('\n'.join(current_content))
            
        return sections
        
    def _process_section_content(self, content):
        """處理區段內容，嘗試解析 JSON"""
        # 如果內容是列表的第一個元素（通常是解析過的 JSON）
        if isinstance(content, list) and len(content) > 0:
            return content[0]
            
        # 嘗試從文本中提取並解析 JSON
        json_blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_blocks:
            try:
                return json.loads(json_blocks[0])
            except json.JSONDecodeError:
                pass
                
        return content.strip()
        
    def get_character_profile(self):
        """獲取角色設定"""
        profile = self.config.get('角色設定')
        if isinstance(profile, dict):
            return profile
        return {}
        
    def get_response_rules(self):
        """獲取回應規則"""
        constraints = self.config.get('限制與警告')
        if isinstance(constraints, dict):
            return constraints
        return {}
        
    def get_system_prompt(self):
        """獲取系統提示詞"""
        templates = self.config.get('提示詞模板')
        if isinstance(templates, dict):
            return templates.get('基礎提示', '')
        return ''
        
    def get_memory_config(self):
        """獲取記憶設定"""
        guidelines = self.config.get('互動指南')
        if isinstance(guidelines, dict) and '記憶管理' in str(guidelines):
            return guidelines
        return {}
        
    def get_system_config(self):
        """獲取系統配置"""
        config = self.config.get('系統配置')
        if isinstance(config, dict):
            return config
        return {} 
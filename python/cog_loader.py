import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Type, Optional

from base_cog import BaseCog

class CogRegistry:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger if logger else logging.getLogger(__name__)
        self.cogs: Dict[str, Type[BaseCog]] = {}
        self.loaded = False
    
    def load_cogs(self):
        if self.loaded:
            return
        
        self.logger.info("Loading cogs...")
        
        current_dir = Path(__file__).parent
        potential_cogs_dir = current_dir / 'cogs'
        
        if potential_cogs_dir.exists() and potential_cogs_dir.is_dir():
            cogs_dir = potential_cogs_dir
            self.logger.info(f"Found cogs directory: {cogs_dir}")
        else:
            cwd_cogs_dir = Path.cwd() / 'cogs'
            if cwd_cogs_dir.exists() and cwd_cogs_dir.is_dir():
                cogs_dir = cwd_cogs_dir
                self.logger.info(f"Found cogs directory: {cogs_dir}")
            else:
                self.logger.error("Could not find cogs directory")
                return
        
        if str(cogs_dir.parent) not in sys.path:
            sys.path.insert(0, str(cogs_dir.parent))
        
        for item in os.listdir(cogs_dir):
            if item.endswith('.py') and not item.startswith('__'):
                module_name = f"cogs.{item[:-3]}"
                
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseCog) and 
                        obj != BaseCog and
                        obj.__module__ == module.__name__):
                        
                        self.cogs[name] = obj
                        self.logger.info(f"Loaded cog: {name}")
        
        self.loaded = True
        self.logger.info(f"Loaded {len(self.cogs)} cogs")
    
    def get_all_cogs(self) -> Dict[str, Type[BaseCog]]:
        if not self.loaded:
            self.load_cogs()
        return self.cogs
    
    def get_cog_by_name(self, name: str) -> Optional[Type[BaseCog]]:
        if not self.loaded:
            self.load_cogs()
        return self.cogs.get(name)
    
    def get_cogs_by_output_tag(self, tag: str) -> List[Type[BaseCog]]:
        if not self.loaded:
            self.load_cogs()
        
        return [
            cog for cog in self.cogs.values()
            if tag in cog.output_tags
        ]
    
    def build_pipeline_for_outputs(
        self, 
        required_outputs: List[str],
        include_cogs: Optional[List[str]] = None,
        exclude_cogs: Optional[List[str]] = None
    ) -> List[str]:
        if not self.loaded:
            self.load_cogs()
        
        included_cogs = set()
        excluded_cogs = set()
        
        if include_cogs:
            for cog_name in include_cogs:
                cog_class = self.get_cog_by_name(cog_name)
                if cog_class:
                    included_cogs.add(cog_class)
                else:
                    self.logger.warning(f"Included cog not found: {cog_name}")
        
        if exclude_cogs:
            for cog_name in exclude_cogs:
                cog_class = self.get_cog_by_name(cog_name)
                if cog_class:
                    excluded_cogs.add(cog_class)
                else:
                    self.logger.warning(f"Excluded cog not found: {cog_name}")
        
        dependency_graph = {}
        needed_tags = set(required_outputs)
        available_tags = set()
        pipeline_cogs = set()
        
        for cog_class in included_cogs:
            pipeline_cogs.add(cog_class)
            dependency_graph[cog_class] = set()
            available_tags.update(cog_class.output_tags)
        
        for tag in required_outputs:
            cogs_for_tag = self.get_cogs_by_output_tag(tag)
            for cog_class in cogs_for_tag:
                if cog_class not in excluded_cogs:
                    pipeline_cogs.add(cog_class)
                    dependency_graph[cog_class] = set()
                    available_tags.update(cog_class.output_tags)
        
        if not pipeline_cogs and required_outputs:
            self.logger.error(f"No cogs found that produce required outputs: {required_outputs}")
            return []
        
        added = True
        while added:
            added = False
            
            for cog_class in list(pipeline_cogs):
                unsatisfied = set(cog_class.input_tags) - available_tags
                
                if unsatisfied:
                    for tag in unsatisfied:
                        providers = self.get_cogs_by_output_tag(tag)
                        
                        if providers:
                            for provider in providers:
                                if provider not in pipeline_cogs and provider not in excluded_cogs:
                                    pipeline_cogs.add(provider)
                                    dependency_graph[provider] = set()
                                    available_tags.update(provider.output_tags)
                                    added = True
                                
                                if provider in pipeline_cogs:
                                    dependency_graph[cog_class].add(provider)
                        else:
                            self.logger.warning(f"No cog found that produces tag: {tag}")
        
        unsatisfied = needed_tags - available_tags
        if unsatisfied:
            self.logger.error(f"Cannot satisfy all required outputs: {unsatisfied}")
            return []
        
        sorted_cogs = []
        visited = set()
        temp_mark = set()
        
        def visit(cog):
            if cog in temp_mark:
                raise ValueError(f"Cyclic dependency detected involving {cog.__name__}")
            
            if cog not in visited:
                temp_mark.add(cog)
                
                for dep in dependency_graph[cog]:
                    visit(dep)
                
                temp_mark.remove(cog)
                visited.add(cog)
                sorted_cogs.append(cog)
        
        for cog in list(pipeline_cogs):
            if cog not in visited:
                visit(cog)
        
        sorted_cog_names = [cog.__name__ for cog in reversed(sorted_cogs)]
        self.logger.info(f"Built pipeline with {len(sorted_cog_names)} cogs: {sorted_cog_names}")
        
        return sorted_cog_names
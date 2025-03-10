"""
@file cog_loader.py
@brief Dynamic cog loading and pipeline building.
"""
import importlib
import inspect
import pkgutil
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Type, Set, Optional, Any

from base_cog import BaseCog
from config import Config


class CogRegistry:
    """Registry for cog classes with dynamic loading capabilities."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the registry.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.cogs: Dict[str, Type[BaseCog]] = {}
        self.loaded = False
    
    def load_cogs(self):
        """Discover and load all available cogs."""
        if self.loaded:
            return
        
        self.logger.info("Loading cogs...")
        
        try:
            # Find the directory containing the cogs - handle both package and direct imports
            cogs_dir = None
            
            # Try to find cogs directory relative to current file
            current_dir = Path(__file__).parent
            potential_cogs_dir = current_dir / 'cogs'
            
            if potential_cogs_dir.exists() and potential_cogs_dir.is_dir():
                cogs_dir = potential_cogs_dir
                self.logger.info(f"Found cogs directory: {cogs_dir}")
            else:
                # Try to find relative to current working directory
                cwd_cogs_dir = Path.cwd() / 'cogs'
                if cwd_cogs_dir.exists() and cwd_cogs_dir.is_dir():
                    cogs_dir = cwd_cogs_dir
                    self.logger.info(f"Found cogs directory: {cogs_dir}")
                else:
                    self.logger.error("Could not find cogs directory")
                    return
            
            # Add cogs directory to path if needed
            if str(cogs_dir.parent) not in sys.path:
                sys.path.insert(0, str(cogs_dir.parent))
            
            # Import all cog modules manually
            for item in os.listdir(cogs_dir):
                if item.endswith('.py') and not item.startswith('__'):
                    module_name = f"cogs.{item[:-3]}"  # Remove .py extension
                    
                    try:
                        # Try to import the module
                        module = importlib.import_module(module_name)
                        
                        # Find cog classes in the module
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, BaseCog) and 
                                obj != BaseCog and
                                obj.__module__ == module.__name__):
                                
                                # Register the cog
                                self.cogs[name] = obj
                                self.logger.info(f"Loaded cog: {name}")
                    
                    except Exception as e:
                        self.logger.error(f"Error loading cog module {module_name}: {e}")
            
            self.loaded = True
            self.logger.info(f"Loaded {len(self.cogs)} cogs")
            
        except Exception as e:
            self.logger.error(f"Error loading cogs: {e}")
    
    def get_all_cogs(self) -> Dict[str, Type[BaseCog]]:
        """Get all loaded cogs.
        
        Returns:
            Dict[str, Type[BaseCog]]: Dictionary of cog name to class
        """
        if not self.loaded:
            self.load_cogs()
        
        return self.cogs
    
    def get_cog_by_name(self, name: str) -> Optional[Type[BaseCog]]:
        """Get a cog class by name.
        
        Args:
            name: Name of the cog class
        
        Returns:
            Optional[Type[BaseCog]]: Cog class if found, None otherwise
        """
        if not self.loaded:
            self.load_cogs()
        
        return self.cogs.get(name)
    
    def get_cogs_by_output_tag(self, tag: str) -> List[Type[BaseCog]]:
        """Get cogs that produce a specific output tag.
        
        Args:
            tag: Output tag to search for
        
        Returns:
            List[Type[BaseCog]]: List of cog classes
        """
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
    ) -> List[BaseCog]:
        """Build a pipeline of cogs that produces the required outputs.
        
        Args:
            required_outputs: List of required output tags
            include_cogs: List of cog names that must be included
            exclude_cogs: List of cog names that must be excluded
            
        Returns:
            List[BaseCog]: List of cog instances in processing order
        """
        if not self.loaded:
            self.load_cogs()
        
        # Process include/exclude lists
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
        
        # Create a dependency graph
        dependency_graph = {}
        
        # Keep track of needed tags
        needed_tags = set(required_outputs)
        available_tags = set()
        
        # Initialize with cogs that provide the required outputs
        pipeline_cogs = set()
        
        # First, add all explicitly included cogs
        for cog_class in included_cogs:
            pipeline_cogs.add(cog_class)
            dependency_graph[cog_class] = set()
            available_tags.update(cog_class.output_tags)
            
        # Then add cogs that provide the required outputs
        for tag in required_outputs:
            cogs_for_tag = self.get_cogs_by_output_tag(tag)
            for cog_class in cogs_for_tag:
                if cog_class not in excluded_cogs:
                    pipeline_cogs.add(cog_class)
                    dependency_graph[cog_class] = set()
                    available_tags.update(cog_class.output_tags)
        
        # No cogs found for required outputs
        if not pipeline_cogs and required_outputs:
            self.logger.error(f"No cogs found that produce required outputs: {required_outputs}")
            return []
        
        # Expand with dependencies until no new dependencies are found
        added = True
        while added:
            added = False
            
            # Find cogs that need to be added based on dependencies
            for cog_class in list(pipeline_cogs):
                # Get input tags that are not satisfied
                unsatisfied = set(cog_class.input_tags) - available_tags
                
                if unsatisfied:
                    # Find cogs that provide these tags
                    for tag in unsatisfied:
                        providers = self.get_cogs_by_output_tag(tag)
                        
                        if providers:
                            for provider in providers:
                                if provider not in pipeline_cogs and provider not in excluded_cogs:
                                    pipeline_cogs.add(provider)
                                    dependency_graph[provider] = set()
                                    available_tags.update(provider.output_tags)
                                    added = True
                                
                                # Add dependency
                                if provider in pipeline_cogs:
                                    dependency_graph[cog_class].add(provider)
                        else:
                            self.logger.warning(f"No cog found that produces tag: {tag}")
        
        # Check if all needed tags are available
        unsatisfied = needed_tags - available_tags
        if unsatisfied:
            self.logger.error(f"Cannot satisfy all required outputs: {unsatisfied}")
            return []
        
        # Perform topological sort to determine processing order
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
        
        # Sort
        for cog in list(pipeline_cogs):
            if cog not in visited:
                visit(cog)
        
        # Instantiate cogs in reverse order (dependencies first)
        instantiated_cogs = []
        for cog_class in reversed(sorted_cogs):
            try:
                # Handle special cases for cogs that need parameters
                if cog_class.__name__ == "AcoustIDCog":
                    instantiated_cogs.append(
                        cog_class(
                            api_key=Config.ACOUSTID_API_KEY,
                            fpcalc_path=Config.get_fpcalc_path(),
                            logger=self.logger
                        )
                    )
                else:
                    instantiated_cogs.append(cog_class(logger=self.logger))
            except Exception as e:
                self.logger.error(f"Error instantiating {cog_class.__name__}: {e}")
        
        self.logger.info(f"Built pipeline with {len(instantiated_cogs)} cogs: {[c.__class__.__name__ for c in instantiated_cogs]}")
        
        return instantiated_cogs


def build_pipeline(registry: CogRegistry, selected_cogs: List[str]) -> List[BaseCog]:
    """Build a pipeline from a list of cog names.
    
    Args:
        registry: Cog registry
        selected_cogs: List of cog names
    
    Returns:
        List[BaseCog]: List of cog instances
    """
    logger = logging.getLogger(__name__)
    
    # Make sure cogs are loaded
    if not registry.loaded:
        registry.load_cogs()
    
    # Get cog classes
    pipeline_cogs = []
    for name in selected_cogs:
        cog_class = registry.get_cog_by_name(name)
        if cog_class:
            try:
                # Handle special cases for cogs that need parameters
                if cog_class.__name__ == "AcoustIDCog":
                    pipeline_cogs.append(
                        cog_class(
                            api_key=Config.ACOUSTID_API_KEY,
                            fpcalc_path=Config.get_fpcalc_path(),
                            logger=logger
                        )
                    )
                else:
                    pipeline_cogs.append(cog_class(logger=logger))
            except Exception as e:
                logger.error(f"Error instantiating cog {name}: {e}")
        else:
            logger.error(f"Cog not found: {name}")
    
    return pipeline_cogs
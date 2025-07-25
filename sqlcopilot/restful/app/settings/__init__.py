"""
配置作用优先级（从高到低）：
1. 环境变量
2. config.env.yaml
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Any, Dict
from pathlib import Path


# 读取 YAML 配置文件
def load_yaml_config(env: str) -> Dict[str, Any]:
    config_file = Path(__file__).parent / Path(f"config.{env}.yaml")
    print(f"Loading config from {config_file}")
    if config_file.exists():
        with config_file.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    else:
        print(f"Warning: {config_file} not found, using empty config.")
        return {}


def merge_env_overrides(config: Dict[str, Any], prefix=""):
    """
    Recursively overrides config dictionary with environment variables.
    e.g. ELASTICSEARCH_URL overrides config['elasticsearch']['url']
    """
    for key, value in config.items():
        env_var_name = f"{prefix}{key}".upper()
        if isinstance(value, dict):
            merge_env_overrides(value, f"{env_var_name}_")
        else:
            env_value = os.getenv(env_var_name)
            if env_value is not None:
                # Attempt to cast to the same type as the original value
                try:
                    config[key] = type(value)(env_value)
                except (ValueError, TypeError):
                    config[key] = env_value


class NoneProxy:
    """代理对象，使得访问None的任何属性都返回None"""

    def __getattr__(self, item):
        return None


class NestedConfig:
    def __init__(self, data: Dict[str, Any]):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, NestedConfig(value))
            else:
                setattr(self, key, value)

    def __getattr__(self, item):
        # 如果属性不存在，返回None而不是抛出异常
        return NoneProxy()

    def __repr__(self):
        return str(self.__dict__)


@dataclass
class Config:
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.nested = NestedConfig(self.data)

    def __getattr__(self, item):
        value = getattr(self.nested, item)
        if value is None:
            return NoneProxy()
        return value

    def __repr__(self):
        def _format_nested(obj, prefix=""):
            result = []
            for k, v in obj.__dict__.items():
                if isinstance(v, NestedConfig):
                    nested_prefix = f"{prefix}.{k}" if prefix else k
                    result.extend(_format_nested(v, nested_prefix))
                else:
                    full_key = f"{prefix}.{k}" if prefix else k
                    result.append(f"{full_key}={v}")
            return result

        return "\nAPP CONFIGS:\n" + "\n".join(_format_nested(self.nested))


# 读取环境变量
env = os.getenv("ENV", "dev")
# 项目枚举：default/audit，default为默认项目，audit为德州审计项目专用项目
config_data = load_yaml_config(env)
merge_env_overrides(config_data)

# 初始化配置
config = Config(config_data)

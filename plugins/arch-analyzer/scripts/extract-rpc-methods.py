#!/usr/bin/env python3
"""
提取服务暴露的 RPC 方法列表

用法:
    python3 extract-rpc-methods.py <service-name>

输出:
    1. 打印需要查询 XRay 的方法列表
    2. 生成 docs/rpc-analysis/<service>-methods.json
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


def find_rpc_servers(project_path: Path) -> List[Dict]:
    """查找所有 RPC Server 实现"""
    servers = []

    # 查找 implements XxxService.Iface 的文件
    for java_file in project_path.glob('**/*.java'):
        try:
            content = java_file.read_text(encoding='utf-8')

            # 提取接口名
            iface_match = re.search(r'implements\s+(\w+)\.Iface', content)
            if not iface_match:
                continue

            interface_name = iface_match.group(1)

            # 提取公开方法（@Override 注解后的方法）
            methods = []
            override_pattern = r'@Override\s+public\s+\w+\s+(\w+)\s*\('
            for match in re.finditer(override_pattern, content):
                method_name = match.group(1)
                if not method_name.startswith('_'):
                    methods.append(method_name)

            if methods:
                servers.append({
                    'file': str(java_file.relative_to(project_path)),
                    'interface': interface_name,
                    'methods': sorted(set(methods))
                })

        except Exception as e:
            print(f"警告: 无法处理文件 {java_file}: {e}")

    return servers


def resolve_project_path(path_or_name: str) -> str:
    """解析项目路径"""
    if os.path.isdir(path_or_name):
        return path_or_name

    current_dir = Path.cwd()
    candidate = current_dir / path_or_name
    if candidate.is_dir():
        return str(candidate)

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    candidate = repo_root / path_or_name
    if candidate.is_dir():
        return str(candidate)

    return path_or_name


def main():
    parser = argparse.ArgumentParser(description='提取 RPC Server 方法列表')
    parser.add_argument('service_name', help='服务名称')
    parser.add_argument('--output', '-o', help='输出文件路径')

    args = parser.parse_args()

    project_path = Path(resolve_project_path(args.service_name))

    if not project_path.is_dir():
        print(f"错误: 项目路径不存在: {args.service_name}")
        return 1

    service_name = project_path.name

    print(f"\n分析服务: {service_name}")
    print("=" * 60)

    servers = find_rpc_servers(project_path)

    if not servers:
        print("未找到 RPC Server 实现")
        return 1

    # 收集所有方法
    all_methods = set()
    for server in servers:
        all_methods.update(server['methods'])

    # 打印结果
    print(f"\n找到 {len(servers)} 个 RPC Server，共 {len(all_methods)} 个方法\n")

    for server in servers:
        print(f"📄 {server['interface']}:")
        for method in server['methods']:
            print(f"   • {method}")
        print()

    # 生成 XRay 查询命令
    print("=" * 60)
    print("XRay 查询命令（复制执行）:")
    print("=" * 60)

    app_name = f"{service_name}-service-default"
    for method in sorted(all_methods)[:10]:  # 只显示前 10 个
        print(f"""
query_downstream_services(
    app="{app_name}",
    service="{method}",
    edgeType="Service",
    days=14
)""")

    if len(all_methods) > 10:
        print(f"\n... 还有 {len(all_methods) - 10} 个方法")

    # 保存到文件（输出到项目目录下）
    output_dir = project_path / 'docs' / 'rpc-analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output or str(output_dir / f'{service_name}-methods.json')

    result = {
        'project': service_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d'),
        'appName': app_name,
        'servers': servers,
        'allMethods': sorted(all_methods)
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 方法列表已保存到: {output_path}")

    return 0


if __name__ == '__main__':
    exit(main())

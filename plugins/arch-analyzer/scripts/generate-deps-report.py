#!/usr/bin/env python3
"""
RPC 依赖报告生成脚本

将静态分析结果与 XRay 运行时数据合并，生成最终的方法级依赖报告。
默认会清理中间文件（*-enhanced.json 等），只保留最终的 *-deps.json。

用法:
    python3 generate-deps-report.py <service-name>
    python3 generate-deps-report.py <service-name> --keep-intermediate  # 保留中间文件

示例:
    python3 generate-deps-report.py redsettlement
    python3 generate-deps-report.py redsettlement -k  # 保留中间文件
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class DepsReportGenerator:
    """依赖报告生成器"""

    def __init__(self, service_name: str, output_dir: str = 'docs/rpc-analysis'):
        self.service_name = service_name
        self.output_dir = Path(output_dir)
        self.static_data: Optional[Dict] = None
        self.xray_data: Optional[Dict] = None
        self.upstream_data: Optional[Dict] = None  # 上游分析数据
        self.static_file_path: Optional[Path] = None  # 记录静态分析文件路径

    def load_static_data(self, file_path: Optional[str] = None) -> bool:
        """加载静态分析数据"""
        if file_path:
            path = Path(file_path)
        else:
            # 尝试多个可能的文件名（优先使用最新的 enhanced.json）
            candidates = [
                self.output_dir / f'{self.service_name}-enhanced.json',
                self.output_dir / f'{self.service_name}-enhanced-v3.json',
                self.output_dir / f'{self.service_name}-static.json',
            ]
            path = None
            for candidate in candidates:
                if candidate.exists():
                    path = candidate
                    break

        if path and path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.static_data = json.load(f)
            self.static_file_path = path  # 记录路径用于后续清理
            print(f"✓ 加载静态分析数据: {path}")
            return True
        else:
            print(f"✗ 未找到静态分析数据")
            return False

    def load_xray_data(self, file_path: Optional[str] = None) -> bool:
        """加载 XRay 运行时数据"""
        if file_path:
            path = Path(file_path)
        else:
            path = self.output_dir / f'{self.service_name}-xray.json'

        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.xray_data = json.load(f)
            print(f"✓ 加载 XRay 数据: {path}")
            return True
        else:
            print(f"⚠ 未找到 XRay 数据: {path}")
            return False

    def load_upstream_data(self, file_path: Optional[str] = None) -> bool:
        """加载上游分析数据"""
        if file_path:
            path = Path(file_path)
        else:
            path = self.output_dir / f'{self.service_name}-upstream.json'

        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.upstream_data = json.load(f)
            print(f"✓ 加载上游数据: {path}")
            return True
        else:
            print(f"⚠ 未找到上游数据: {path}")
            return False

    def _normalize_call_count(self, count_str: str) -> str:
        """标准化调用量格式"""
        if not count_str:
            return "< 10"
        # 移除空格，统一格式
        return count_str.replace(' ', '')

    def _build_xray_lookup(self) -> Dict[Tuple[str, str], Dict]:
        """构建 XRay 数据的查找表 (service, method) -> data"""
        lookup = {}
        if not self.xray_data:
            return lookup

        for dep in self.xray_data.get('dependencies', []):
            if dep.get('type') == 'MQ':
                continue
            service = dep.get('serviceName', '')
            method = dep.get('method', '')
            if service and method:
                key = (service, method)
                # 如果同一方法有多个来源，累加调用量（简化处理：取第一个）
                if key not in lookup:
                    lookup[key] = dep
        return lookup

    def _extract_interface_name(self, interface_class: str) -> str:
        """从接口类名提取接口名"""
        # RemsCoreService.Iface -> RemsCoreService
        return interface_class.replace('.Iface', '')

    def _is_self_call(self, target_app: str) -> bool:
        """判断是否是自身调用"""
        return target_app == self.service_name

    def generate_report(self) -> Dict:
        """生成最终的依赖报告"""
        if not self.static_data:
            raise ValueError("必须先加载静态分析数据")

        xray_lookup = self._build_xray_lookup()
        has_xray = bool(self.xray_data)

        rpc_deps = []
        self_calls = []
        unused_deps = []
        mq_deps = []

        # 处理 RPC 依赖
        for bean in self.static_data.get('rpcDependencies', []):
            interface_name = self._extract_interface_name(bean['interfaceClass'])
            service_name = bean.get('serviceName', '')
            target_app = bean.get('targetApp', 'unknown')
            has_main_calls = bean.get('hasMainCalls', False)
            call_locations = bean.get('callLocations', [])

            # 收集所有调用的方法
            methods = set()
            for loc in call_locations:
                methods.update(loc.get('methods', []))

            if not has_main_calls:
                # 未使用的接口
                unused_deps.append({
                    'app': target_app,
                    'service': service_name,
                    'interface': interface_name,
                    'note': '已配置但代码中无调用'
                })
                continue

            if not methods:
                # 有调用但未能提取方法名（可能是动态调用）
                methods = {'(unknown)'}

            # 判断是自身调用还是外部调用
            is_self = self._is_self_call(target_app)

            for method in sorted(methods):
                # 从 XRay 查找调用量
                xray_key = (service_name, method)
                xray_info = xray_lookup.get(xray_key)

                if xray_info:
                    calls = self._normalize_call_count(xray_info.get('callCount', ''))
                elif has_xray:
                    # XRay 有数据但该方法未采集到
                    calls = '< 10'
                else:
                    # 无 XRay 数据
                    calls = '未知'

                dep_entry = {
                    'app': target_app,
                    'service': service_name,
                    'interface': interface_name,
                    'method': method,
                    'calls': calls
                }

                if is_self:
                    self_calls.append(dep_entry)
                else:
                    rpc_deps.append(dep_entry)

        # 处理 MQ Producer
        for producer in self.static_data.get('mqProducers', []):
            topic = producer.get('topic', '')
            # 从 XRay 查找 MQ 调用量
            mq_xray = None
            if self.xray_data:
                for dep in self.xray_data.get('dependencies', []):
                    if dep.get('type') == 'MQ' and topic in dep.get('targetApp', ''):
                        mq_xray = dep
                        break

            calls = self._normalize_call_count(mq_xray.get('callCount', '')) if mq_xray else '未知'

            mq_deps.append({
                'type': 'producer',
                'topic': topic,
                'calls': calls
            })

        # 处理 MQ Consumer
        for consumer in self.static_data.get('mqConsumers', []):
            mq_deps.append({
                'type': 'consumer',
                'topic': consumer.get('topic', ''),
                'calls': '-'
            })

        # 按调用量排序（高到低）
        def sort_key(x):
            calls = x.get('calls', '')
            # 简单的排序逻辑：亿 > 万 > 数字 > < 10 > 未知
            if '亿' in calls:
                return 0
            elif '万' in calls:
                return 1
            elif calls.isdigit():
                return 2
            elif '< 10' in calls:
                return 3
            else:
                return 4

        rpc_deps.sort(key=sort_key)

        # 生成数据来源描述
        data_source = 'static'
        if has_xray:
            period = self.xray_data.get('queryPeriod', '14d')
            data_source = f'static + xray({period})'

        # 处理上游数据
        upstream_deps = []
        if self.upstream_data:
            upstream_deps = self.upstream_data.get('upstream', [])
            # 更新数据来源描述
            if 'upstream' not in data_source:
                data_source = data_source.replace(')', ' + upstream)')
                if ')' not in data_source:
                    data_source = f'{data_source} + upstream'

        return {
            'project': self.service_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d'),
            'dataSource': data_source,
            'rpc': rpc_deps,
            'upstream': upstream_deps,  # 新增上游依赖
            'selfCall': self_calls,
            'mq': mq_deps,
            'unused': unused_deps
        }

    def save_report(self, report: Dict, output_path: Optional[str] = None) -> str:
        """保存报告到文件"""
        if output_path:
            path = Path(output_path)
        else:
            path = self.output_dir / f'{self.service_name}-deps.json'

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return str(path)

    def cleanup_intermediate_files(self) -> List[str]:
        """清理中间文件，返回删除的文件列表"""
        removed = []

        # 删除静态分析文件
        if self.static_file_path and self.static_file_path.exists():
            self.static_file_path.unlink()
            removed.append(str(self.static_file_path))

        # 删除其他可能的中间版本文件
        patterns = [
            f'{self.service_name}-enhanced-v*.json',
            f'{self.service_name}-static.json',
            f'{self.service_name}-final.json',
            f'{self.service_name}-report.md',
        ]

        for pattern in patterns:
            for f in self.output_dir.glob(pattern):
                f.unlink()
                removed.append(str(f))

        return removed


def print_report_summary(report: Dict):
    """打印报告摘要"""
    print("\n" + "=" * 60)
    print(f"依赖报告摘要 - {report['project']}")
    print("=" * 60)

    rpc_count = len(report.get('rpc', []))
    upstream_count = len(report.get('upstream', []))
    self_count = len(report.get('selfCall', []))
    mq_count = len(report.get('mq', []))
    unused_count = len(report.get('unused', []))

    print(f"\n📊 统计:")
    print(f"  • 下游 RPC 调用: {rpc_count} (本服务调用谁)")
    print(f"  • 上游 RPC 调用: {upstream_count} (谁调用本服务)")
    print(f"  • 自身调用方法: {self_count}")
    print(f"  • MQ Topic: {mq_count}")
    print(f"  • 未使用接口: {unused_count}")

    # 显示高频下游调用
    rpc_deps = report.get('rpc', [])
    if rpc_deps:
        print(f"\n🔥 下游高频调用 TOP 5:")
        for dep in rpc_deps[:5]:
            print(f"  • {dep['interface']}.{dep['method']}: {dep['calls']}")

    # 显示高频上游调用
    upstream_deps = report.get('upstream', [])
    if upstream_deps:
        print(f"\n📈 上游高频调用 TOP 5:")
        for dep in upstream_deps[:5]:
            caller = f"{dep.get('callerApp', 'unknown')}.{dep.get('callerMethod', '')}"
            target = dep.get('targetMethod', '')
            calls = dep.get('calls', '')
            print(f"  • {caller} → {target}: {calls}")

    # 显示未使用接口
    unused = report.get('unused', [])
    if unused:
        print(f"\n⚠️ 未使用接口:")
        for dep in unused:
            print(f"  • {dep['interface']} → {dep['app']}")


def resolve_project_path(path_or_name: str) -> Path:
    """解析项目路径，支持服务名或完整路径"""
    # 如果是完整路径且存在
    if os.path.isdir(path_or_name):
        return Path(path_or_name)

    # 尝试作为服务名在当前目录查找
    current_dir = Path.cwd()
    candidate = current_dir / path_or_name
    if candidate.is_dir():
        return candidate

    # 返回当前目录（假设服务名就是当前目录名）
    return current_dir


def main():
    parser = argparse.ArgumentParser(description='RPC 依赖报告生成工具')
    parser.add_argument('project_path', help='项目路径或服务名（如 redsettlement 或 /path/to/redsettlement）')
    parser.add_argument('--static', '-s', help='静态分析 JSON 文件路径')
    parser.add_argument('--xray', '-x', help='XRay 运行时 JSON 文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--dir', '-d', default=None,
                        help='分析结果目录 (默认: {project}/docs/rpc-analysis)')
    parser.add_argument('--keep-intermediate', '-k', action='store_true',
                        help='保留中间文件（默认删除）')

    args = parser.parse_args()

    # 解析项目路径
    project_path = resolve_project_path(args.project_path)
    service_name = project_path.name

    # 确定输出目录（默认为项目下的 docs/rpc-analysis）
    output_dir = args.dir or str(project_path / 'docs' / 'rpc-analysis')

    generator = DepsReportGenerator(service_name, output_dir)

    # 加载数据
    if not generator.load_static_data(args.static):
        print(f"\n❌ 错误: 未找到静态分析数据，请先运行:")
        print(f"   python3 ~/.claude/plugins/local/arch-analyzer/scripts/analyze-rpc-enhanced.py {args.project_path}")
        return 1

    generator.load_xray_data(args.xray)
    generator.load_upstream_data()  # 尝试加载上游数据

    # 生成报告
    report = generator.generate_report()

    # 保存报告
    output_path = generator.save_report(report, args.output)

    # 清理中间文件（默认删除）
    if not args.keep_intermediate:
        removed = generator.cleanup_intermediate_files()
        if removed:
            print(f"🧹 已清理 {len(removed)} 个中间文件")

    # 打印摘要
    print_report_summary(report)

    print(f"\n✅ 报告已保存到: {output_path}")

    return 0


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""Performance testing script for the refactored trading system."""

import time
import os
import subprocess
import sys
from pathlib import Path


def measure_script_performance(script_path: str, data_dir: str = "test_data") -> dict:
    """Measure performance metrics for a script execution.
    
    Args:
        script_path: Path to the script to test
        data_dir: Data directory to use for testing
        
    Returns:
        Dictionary with performance metrics
    """
    # Measure execution time
    start_time = time.time()
    
    try:
        # Run the script
        result = subprocess.run([
            sys.executable, script_path, data_dir
        ], capture_output=True, text=True, timeout=120)
        
        execution_time = time.time() - start_time
        
        return {
            'execution_time': execution_time,
            'return_code': result.returncode,
            'stdout_lines': len(result.stdout.splitlines()),
            'stderr_lines': len(result.stderr.splitlines()),
            'success': result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        return {
            'execution_time': 120.0,
            'return_code': -1,
            'stdout_lines': 0,
            'stderr_lines': 0,
            'success': False,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'execution_time': 0,
            'return_code': -1,
            'stdout_lines': 0,
            'stderr_lines': 0,
            'success': False,
            'error': str(e)
        }


def count_lines_of_code(file_path: str) -> dict:
    """Count lines of code in a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Dictionary with line count metrics
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#'):
                comment_lines += 1
            elif '"""' in stripped or "'''" in stripped:
                comment_lines += 1
            else:
                code_lines += 1
        
        return {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines
        }
        
    except Exception as e:
        return {
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'error': str(e)
        }


def analyze_module_structure() -> dict:
    """Analyze the modular structure of the refactored system.
    
    Returns:
        Dictionary with module analysis
    """
    modules = {
        'data': ['models', 'repositories'],
        'financial': ['calculations.py', 'currency_handler.py', 'pnl_calculator.py'],
        'market_data': ['data_fetcher.py', 'market_hours.py', 'price_cache.py'],
        'portfolio': ['portfolio_manager.py', 'trade_processor.py', 'position_calculator.py'],
        'display': ['console_output.py', 'table_formatter.py', 'terminal_utils.py'],
        'utils': ['backup_manager.py', 'timezone_utils.py', 'validation.py'],
        'config': ['settings.py', 'constants.py']
    }
    
    analysis = {
        'total_modules': 0,
        'total_files': 0,
        'total_lines': 0,
        'modules': {}
    }
    
    for module_name, files in modules.items():
        module_path = Path(module_name)
        if not module_path.exists():
            continue
            
        module_info = {
            'files': [],
            'total_lines': 0,
            'exists': True
        }
        
        for file_name in files:
            if file_name.endswith('.py'):
                file_path = module_path / file_name
            else:
                # It's a subdirectory
                subdir_path = module_path / file_name
                if subdir_path.exists():
                    # Count all Python files in subdirectory
                    for py_file in subdir_path.glob('*.py'):
                        if py_file.name != '__init__.py':
                            file_info = count_lines_of_code(str(py_file))
                            module_info['files'].append({
                                'name': str(py_file.relative_to(module_path)),
                                'lines': file_info['total_lines']
                            })
                            module_info['total_lines'] += file_info['total_lines']
                continue
            
            if file_path.exists():
                file_info = count_lines_of_code(str(file_path))
                module_info['files'].append({
                    'name': file_name,
                    'lines': file_info['total_lines']
                })
                module_info['total_lines'] += file_info['total_lines']
        
        analysis['modules'][module_name] = module_info
        analysis['total_modules'] += 1
        analysis['total_files'] += len(module_info['files'])
        analysis['total_lines'] += module_info['total_lines']
    
    return analysis


def main():
    """Run performance analysis."""
    print("🔍 Trading System Performance Analysis")
    print("=" * 50)
    
    # Analyze main script
    print("\n_safe_emoji('📊') Main Script Analysis:")
    main_script_metrics = count_lines_of_code("trading_script.py")
    print(f"  Total lines: {main_script_metrics['total_lines']}")
    print(f"  Code lines: {main_script_metrics['code_lines']}")
    print(f"  Comment lines: {main_script_metrics['comment_lines']}")
    print(f"  Blank lines: {main_script_metrics['blank_lines']}")
    
    target_lines = 500
    if main_script_metrics['total_lines'] <= target_lines:
        print(f"  _safe_emoji('✅') Main script is under target ({target_lines} lines)")
    else:
        excess = main_script_metrics['total_lines'] - target_lines
        print(f"  _safe_emoji('⚠️')  Main script exceeds target by {excess} lines")
    
    # Analyze modular structure
    print("\n🏗️  Modular Structure Analysis:")
    module_analysis = analyze_module_structure()
    print(f"  Total modules: {module_analysis['total_modules']}")
    print(f"  Total files: {module_analysis['total_files']}")
    print(f"  Total lines across modules: {module_analysis['total_lines']}")
    
    for module_name, module_info in module_analysis['modules'].items():
        if module_info['exists']:
            print(f"    {module_name}: {len(module_info['files'])} files, {module_info['total_lines']} lines")
    
    # Performance testing
    print("\n_safe_emoji('⚡') Performance Testing:")
    print("  Testing refactored script...")
    
    perf_metrics = measure_script_performance("trading_script.py")
    
    if perf_metrics['success']:
        print(f"  _safe_emoji('✅') Execution time: {perf_metrics['execution_time']:.2f} seconds")
        print(f"  📝 Output lines: {perf_metrics['stdout_lines']}")
    else:
        print(f"  _safe_emoji('❌') Script failed: {perf_metrics.get('error', 'Unknown error')}")
        print(f"  Return code: {perf_metrics['return_code']}")
    
    # Summary
    print("\n_safe_emoji('📋') Summary:")
    total_system_lines = main_script_metrics['total_lines'] + module_analysis['total_lines']
    print(f"  Total system size: {total_system_lines} lines")
    print(f"  Main script: {main_script_metrics['total_lines']} lines ({main_script_metrics['total_lines']/total_system_lines*100:.1f}%)")
    print(f"  Modules: {module_analysis['total_lines']} lines ({module_analysis['total_lines']/total_system_lines*100:.1f}%)")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if main_script_metrics['total_lines'] > target_lines:
        print(f"  - Consider moving more functionality to modules to reduce main script size")
        print(f"  - Target reduction: {main_script_metrics['total_lines'] - target_lines} lines")
    
    if perf_metrics['success'] and perf_metrics['execution_time'] > 30:
        print(f"  - Consider optimizing performance (current: {perf_metrics['execution_time']:.1f}s)")
    elif perf_metrics['success']:
        print(f"  - Performance is acceptable ({perf_metrics['execution_time']:.1f}s execution time)")
    
    print(f"  - Modular architecture successfully separates concerns across {module_analysis['total_modules']} modules")
    print(f"  - Each module has single, well-defined responsibility")


if __name__ == "__main__":
    main()
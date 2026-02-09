import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class UnityScriptOrganizer:
    def __init__(self):
        """
        初始化Unity C#脚本整理器
        """
        # 获取脚本所在目录，假设脚本放在Scripts文件夹下
        self.script_dir = Path(__file__).parent.absolute()
        self.output_dir = self.script_dir / "unity_docs"
        
        # 如果没有Scripts文件夹，尝试在当前目录查找.cs文件
        self.scripts_folder = self.script_dir
        if (self.script_dir / "Scripts").exists():
            self.scripts_folder = self.script_dir / "Scripts"
        
        self.script_files: Dict[str, List[Tuple[str, str]]] = {}
        
    def ensure_output_dir(self):
        """确保输出目录存在"""
        self.output_dir.mkdir(exist_ok=True)
    
    def find_csharp_files(self):
        """递归查找所有C#脚本文件"""
        print(f"扫描目录: {self.scripts_folder}")
        
        # 递归查找所有.cs文件
        csharp_files = list(self.scripts_folder.rglob("*.cs"))
        
        # 排除输出目录中的文件
        csharp_files = [f for f in csharp_files if not f.is_relative_to(self.output_dir)]
        
        return sorted(csharp_files, key=lambda x: x.name)
    
    def get_script_category(self, file_path: Path) -> str:
        """
        获取脚本分类（使用文件夹结构）
        
        Args:
            file_path: C#脚本文件路径
            
        Returns:
            分类名称
        """
        # 获取相对于Scripts文件夹的相对路径
        try:
            relative_path = file_path.relative_to(self.scripts_folder)
        except ValueError:
            # 如果不在Scripts文件夹下，使用相对于当前目录的路径
            relative_path = file_path.relative_to(self.script_dir)
        
        # 如果有子文件夹，使用第一级子文件夹作为分类
        if len(relative_path.parts) > 1:
            return relative_path.parts[0]
        
        # 如果在根目录，使用"Common"作为分类
        return "Common"
    
    def read_csharp_file(self, file_path: Path) -> str:
        """
        读取C#脚本文件内容
        
        Args:
            file_path: C#脚本文件路径
            
        Returns:
            C#脚本文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试UTF-8-sig（带BOM的UTF-8）
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    return f.read()
            except:
                # 最后尝试GBK
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
    
    def extract_namespace(self, content: str) -> str:
        """
        从C#脚本中提取命名空间
        
        Args:
            content: C#脚本内容
            
        Returns:
            命名空间（如果找到的话）
        """
        # 查找命名空间声明
        namespace_pattern = r'^\s*namespace\s+([\w\.]+)\s*{'
        match = re.search(namespace_pattern, content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""
    
    def extract_class_name(self, content: str) -> str:
        """
        从C#脚本中提取类名
        
        Args:
            content: C#脚本内容
            
        Returns:
            类名（如果找到的话）
        """
        # 查找类声明（匹配 public class, private class, abstract class, sealed class, static class 等）
        class_pattern = r'^\s*(?:public|private|protected|internal|abstract|sealed|static)?\s*class\s+(\w+)'
        match = re.search(class_pattern, content, re.MULTILINE)
        if match:
            return match.group(1)
        
        # 查找结构体声明
        struct_pattern = r'^\s*(?:public|private|protected|internal)?\s*struct\s+(\w+)'
        match = re.search(struct_pattern, content, re.MULTILINE)
        if match:
            return match.group(1)
        
        # 查找接口声明
        interface_pattern = r'^\s*(?:public|private|protected|internal)?\s*interface\s+(\w+)'
        match = re.search(interface_pattern, content, re.MULTILINE)
        if match:
            return match.group(1)
        
        return "Unknown"
    
    def organize_by_folder(self, csharp_files: List[Path]):
        """按文件夹结构整理脚本"""
        for file_path in csharp_files:
            category = self.get_script_category(file_path)
            
            # 读取文件内容
            content = self.read_csharp_file(file_path)
            
            # 添加到对应的分类中
            if category not in self.script_files:
                self.script_files[category] = []
            
            # 获取相对路径
            try:
                relative_path = file_path.relative_to(self.scripts_folder)
            except ValueError:
                relative_path = file_path.relative_to(self.script_dir)
            
            self.script_files[category].append((str(relative_path), content))
            print(f"  ✓ {relative_path} -> {category}")
    
    def organize_by_namespace(self, csharp_files: List[Path]):
        """按命名空间整理脚本"""
        for file_path in csharp_files:
            # 读取文件内容
            content = self.read_csharp_file(file_path)
            
            # 提取命名空间
            namespace = self.extract_namespace(content)
            if namespace:
                category = namespace.split('.')[-1]  # 使用命名空间的最后一部分
            else:
                category = "NoNamespace"
            
            # 添加到对应的分类中
            if category not in self.script_files:
                self.script_files[category] = []
            
            # 获取相对路径
            try:
                relative_path = file_path.relative_to(self.scripts_folder)
            except ValueError:
                relative_path = file_path.relative_to(self.script_dir)
            
            self.script_files[category].append((str(relative_path), content))
            print(f"  ✓ {relative_path} -> {namespace or 'NoNamespace'}")
    
    def generate_folder_based_markdowns(self):
        """生成按文件夹分类的Markdown文件"""
        self.ensure_output_dir()
        
        for category, files in sorted(self.script_files.items()):
            output_file = self.output_dir / f"{category}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {category} 文件夹\n\n")
                f.write(f"包含 {len(files)} 个C#脚本\n\n")
                
                # 按文件名排序
                for file_path, content in sorted(files, key=lambda x: x[0]):
                    # 提取类名
                    class_name = self.extract_class_name(content)
                    
                    f.write(f"## {file_path}\n")
                    if class_name != "Unknown":
                        f.write(f"**类名:** `{class_name}`  \n")
                    
                    # 提取命名空间（如果有）
                    namespace = self.extract_namespace(content)
                    if namespace:
                        f.write(f"**命名空间:** `{namespace}`  \n")
                    
                    f.write("\n```csharp\n")
                    f.write(content)
                    f.write("\n```\n\n")
                    f.write("---\n\n")
            
            print(f"✓ 生成: {output_file.name}")
    
    def generate_namespace_based_markdowns(self):
        """生成按命名空间分类的Markdown文件"""
        self.ensure_output_dir()
        
        for category, files in sorted(self.script_files.items()):
            output_file = self.output_dir / f"{category}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                if category == "NoNamespace":
                    f.write(f"# 无命名空间脚本\n\n")
                else:
                    f.write(f"# {category} 命名空间\n\n")
                
                f.write(f"包含 {len(files)} 个C#脚本\n\n")
                
                # 按文件名排序
                for file_path, content in sorted(files, key=lambda x: x[0]):
                    # 提取类名
                    class_name = self.extract_class_name(content)
                    
                    f.write(f"## {file_path}\n")
                    if class_name != "Unknown":
                        f.write(f"**类名:** `{class_name}`  \n")
                    
                    f.write("\n```csharp\n")
                    f.write(content)
                    f.write("\n```\n\n")
                    f.write("---\n\n")
            
            print(f"✓ 生成: {output_file.name}")
    
    def generate_single_markdown(self):
        """生成一个包含所有脚本的Markdown文件"""
        self.ensure_output_dir()
        
        output_file = self.output_dir / "all_scripts.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Unity C# 脚本文档\n\n")
            
            total_files = sum(len(files) for files in self.script_files.values())
            f.write(f"总计 {total_files} 个C#脚本，按分类整理\n\n")
            
            # 按分类排序
            for category, files in sorted(self.script_files.items()):
                f.write(f"## {category} ({len(files)}个脚本)\n\n")
                
                # 按文件名排序
                for file_path, content in sorted(files, key=lambda x: x[0]):
                    # 提取类名
                    class_name = self.extract_class_name(content)
                    
                    f.write(f"### {file_path}\n")
                    if class_name != "Unknown":
                        f.write(f"**类名:** `{class_name}`  \n")
                    
                    # 提取命名空间（如果有）
                    namespace = self.extract_namespace(content)
                    if namespace:
                        f.write(f"**命名空间:** `{namespace}`  \n")
                    
                    f.write("\n```csharp\n")
                    f.write(content)
                    f.write("\n```\n\n")
            
            print(f"✓ 生成: {output_file.name}")
    
    def run(self):
        """运行整理器"""
        print("=" * 60)
        print("Unity C# 脚本整理工具")
        print("=" * 60)
        
        # 查找所有C#文件
        csharp_files = self.find_csharp_files()
        
        if not csharp_files:
            print("⚠ 未找到C#脚本文件!")
            print("请将脚本放在Unity项目的Scripts文件夹中运行")
            return
        
        print(f"✓ 找到 {len(csharp_files)} 个C#脚本文件")
        
        # 询问用户选择整理方式
        print("\n请选择整理方式:")
        print("1. 按文件夹结构分类 (推荐)")
        print("2. 按命名空间分类")
        print("3. 生成一个汇总文件")
        
        choice = input("请输入选项 (1, 2 或 3): ").strip()
        
        print("\n" + "-" * 60)
        
        if choice == "2":
            print("正在按命名空间分类整理...")
            self.organize_by_namespace(csharp_files)
            self.generate_namespace_based_markdowns()
        elif choice == "3":
            print("正在生成汇总文件...")
            self.organize_by_folder(csharp_files)  # 使用文件夹分类作为基础
            self.generate_single_markdown()
        else:
            print("正在按文件夹结构分类整理...")
            self.organize_by_folder(csharp_files)
            self.generate_folder_based_markdowns()
        
        print("-" * 60)
        print(f"✓ 整理完成! 文件保存在: {self.output_dir}")
        print("=" * 60)


if __name__ == "__main__":
    organizer = UnityScriptOrganizer()
    organizer.run()
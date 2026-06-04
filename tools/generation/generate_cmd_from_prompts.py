#!/usr/bin/env python3
"""Generate cmd.csv from prompt.txt using NLP2CMD with version detection."""

import csv
import sys
from pathlib import Path
from typing import Tuple, Optional

# Add src to path
sys.path.insert(0, './src')

# Try to import NLP2CMD components
try:
    from nlp2cmd.storage.versioned_store import VersionedSchemaStore
    from nlp2cmd.intelligent.version_aware_generator import VersionAwareCommandGenerator
    from nlp2cmd.schema_extraction import DynamicSchemaRegistry
    NLP2CMD_AVAILABLE = True
except ImportError as e:
    print(f"Warning: NLP2CMD not fully available: {e}")
    NLP2CMD_AVAILABLE = False


class CommandGenerator:
    """Generate commands from prompts using NLP2CMD."""
    
    def __init__(self, use_nlp2cmd: bool = True):
        """Initialize generator."""
        self.use_nlp2cmd = use_nlp2cmd and NLP2CMD_AVAILABLE
        self.version_cache = {}
        
        if self.use_nlp2cmd:
            try:
                # Initialize versioned schema store
                self.schema_store = VersionedSchemaStore("./migrated_schemas")
                self.generator = VersionAwareCommandGenerator(self.schema_store)
                print("✅ Using intelligent NLP2CMD generator")
            except Exception as e:
                print(f"⚠️ Failed to initialize NLP2CMD: {e}")
                self.use_nlp2cmd = False
        
        if not self.use_nlp2cmd:
            print("✅ Using simple pattern-based generator")
    
    def generate_command(self, prompt: str) -> Tuple[str, Optional[str]]:
        """Generate command from prompt."""
        if self.use_nlp2cmd:
            try:
                # Use intelligent generator
                command, metadata = self.generator.generate_command(prompt)
                version = metadata.get('detected_version')
                return command, version
            except Exception as e:
                print(f"Warning: NLP2CMD failed for '{prompt}': {e}")
                # Fallback to simple generation
                return self._generate_simple(prompt), None
        else:
            return self._generate_simple(prompt), None
    
    def _generate_simple(self, prompt: str) -> str:
        """Simple pattern-based command generation."""
        prompt_lower = prompt.lower()
        
        # Docker commands
        if 'docker' in prompt_lower:
            if 'container' in prompt_lower and ('list' in prompt_lower or 'show' in prompt_lower):
                return 'docker ps'
            elif 'image' in prompt_lower and ('list' in prompt_lower or 'show' in prompt_lower):
                return 'docker images'
            elif 'run' in prompt_lower and 'nginx' in prompt_lower:
                return 'docker run -d -p 80:80 nginx'
            elif 'stop' in prompt_lower and 'container' in prompt_lower:
                return 'docker stop $(docker ps -q)'
            elif 'remove' in prompt_lower and 'image' in prompt_lower:
                return 'docker rmi $(docker images -f "dangling=true" -q)'
            elif 'logs' in prompt_lower:
                return 'docker logs -f <container_id>'
            elif 'build' in prompt_lower:
                return 'docker build -t <image_name> .'
            elif 'exec' in prompt_lower:
                return 'docker exec -it <container_id> <command>'
        
        # Kubernetes commands
        elif 'kubectl' in prompt_lower or 'kubernetes' in prompt_lower:
            if 'pod' in prompt_lower and ('list' in prompt_lower or 'show' in prompt_lower):
                return 'kubectl get pods'
            elif 'service' in prompt_lower:
                return 'kubectl get services'
            elif 'deployment' in prompt_lower and ('list' in prompt_lower or 'show' in prompt_lower):
                return 'kubectl get deployments'
            elif 'describe' in prompt_lower and 'pod' in prompt_lower:
                return 'kubectl describe pod <pod_name>'
            elif 'logs' in prompt_lower:
                return 'kubectl logs <pod_name>'
            elif 'apply' in prompt_lower or 'deploy' in prompt_lower:
                return 'kubectl apply -f <yaml_file>'
            elif 'delete' in prompt_lower and 'pod' in prompt_lower:
                return 'kubectl delete pod <pod_name>'
            elif 'scale' in prompt_lower:
                return 'kubectl scale deployment <deployment_name> --replicas=<count>'
        
        # Git commands
        elif 'git' in prompt_lower:
            if 'status' in prompt_lower:
                return 'git status'
            elif 'commit' in prompt_lower and ('history' in prompt_lower or 'log' in prompt_lower):
                return 'git log --oneline -10'
            elif 'branch' in prompt_lower and ('new' in prompt_lower or 'create' in prompt_lower):
                return 'git checkout -b <branch_name>'
            elif 'switch' in prompt_lower or 'checkout' in prompt_lower:
                return 'git checkout <branch_name>'
            elif 'push' in prompt_lower:
                return 'git push origin <branch_name>'
            elif 'pull' in prompt_lower:
                return 'git pull origin <branch_name>'
            elif 'add' in prompt_lower:
                return 'git add .'
            elif 'commit' in prompt_lower:
                return 'git commit -m "<message>"'
            elif 'merge' in prompt_lower:
                return 'git merge <branch_name>'
            elif 'clone' in prompt_lower:
                return 'git clone <repository_url>'
        
        # File operations
        elif 'find' in prompt_lower:
            if 'python' in prompt_lower:
                return 'find . -name "*.py" -type f'
            elif 'javascript' in prompt_lower or 'js' in prompt_lower:
                return 'find . -name "*.js" -type f'
            elif 'large' in prompt_lower and ('size' in prompt_lower or 'mb' in prompt_lower or 'gb' in prompt_lower):
                return 'find . -type f -size +100M'
            elif 'modified' in prompt_lower and ('day' in prompt_lower or 'time' in prompt_lower):
                return 'find . -mtime -7 -type f'
            elif 'empty' in prompt_lower:
                return 'find . -type f -empty'
        
        elif 'grep' in prompt_lower or 'search' in prompt_lower:
            if 'todo' in prompt_lower:
                return 'grep -r "TODO" . --include="*.py" --include="*.js"'
            elif 'pattern' in prompt_lower:
                return 'grep -r "<pattern>" .'
            elif 'file' in prompt_lower:
                return 'grep "<pattern>" <file>'
        
        elif 'count' in prompt_lower:
            if 'line' in prompt_lower and ('code' in prompt_lower or 'python' in prompt_lower):
                return 'find . -name "*.py" -exec wc -l {} + | tail -1'
            elif 'file' in prompt_lower:
                return 'ls -1 | wc -l'
            elif 'word' in prompt_lower:
                return 'wc -w <file>'
        
        elif 'remove' in prompt_lower or 'delete' in prompt_lower:
            if 'temporary' in prompt_lower or 'temp' in prompt_lower:
                return 'find . -name "*.tmp" -delete'
            elif 'file' in prompt_lower:
                return 'rm <file>'
            elif 'directory' in prompt_lower or 'folder' in prompt_lower:
                return 'rm -rf <directory>'
        
        elif 'copy' in prompt_lower or 'cp' in prompt_lower:
            if 'backup' in prompt_lower:
                return 'cp -r <source> <backup_dir>'
            else:
                return 'cp -r <source> <destination>'
        
        elif 'move' in prompt_lower or 'mv' in prompt_lower:
            return 'mv <source> <destination>'
        
        elif 'compress' in prompt_lower or 'zip' in prompt_lower or 'tar' in prompt_lower:
            if 'tar' in prompt_lower and 'gz' in prompt_lower:
                return 'tar -czf <archive>.tar.gz <directory>'
            elif 'zip' in prompt_lower:
                return 'zip -r <archive>.zip <directory>'
        
        elif 'extract' in prompt_lower:
            if 'tar' in prompt_lower or 'gz' in prompt_lower:
                return 'tar -xzf <archive>.tar.gz'
            elif 'zip' in prompt_lower:
                return 'unzip <archive>.zip'
        
        # System monitoring
        elif 'process' in prompt_lower:
            if 'running' in prompt_lower:
                return 'ps aux'
            elif 'kill' in prompt_lower:
                return 'kill -9 <pid>'
        
        elif 'memory' in prompt_lower or 'ram' in prompt_lower:
            return 'free -h'
        
        elif 'disk' in prompt_lower or 'space' in prompt_lower:
            return 'df -h'
        
        elif 'uptime' in prompt_lower:
            return 'uptime'
        
        elif 'network' in prompt_lower or 'connection' in prompt_lower:
            if 'port' in prompt_lower:
                return 'netstat -tuln | grep <port>'
            else:
                return 'netstat -tuln'
        
        elif 'cpu' in prompt_lower:
            return 'top -bn1 | head -20'
        
        elif 'load' in prompt_lower:
            return 'uptime'
        
        elif 'temperature' in prompt_lower or 'temp' in prompt_lower:
            return 'sensors'
        
        elif 'mount' in prompt_lower or 'filesystem' in prompt_lower:
            return 'df -h'
        
        # Network operations
        elif 'ping' in prompt_lower:
            if 'google' in prompt_lower:
                return 'ping -c 4 google.com'
            else:
                return 'ping -c 4 <host>'
        
        elif 'download' in prompt_lower:
            if 'wget' in prompt_lower:
                return 'wget <url>'
            else:
                return 'curl -O <url>'
        
        elif 'curl' in prompt_lower:
            if 'header' in prompt_lower:
                return 'curl -I <url>'
            else:
                return 'curl <url>'
        
        elif 'trace' in prompt_lower or 'traceroute' in prompt_lower:
            return 'traceroute <host>'
        
        # Development tools
        elif 'python' in prompt_lower:
            if 'install' in prompt_lower and 'pip' in prompt_lower:
                return 'pip install <package>'
            elif 'run' in prompt_lower:
                return 'python3 <script>.py'
        
        elif 'npm' in prompt_lower:
            if 'install' in prompt_lower:
                return 'npm install <package>'
            elif 'run' in prompt_lower:
                return 'npm run <script>'
        
        elif 'node' in prompt_lower:
            return 'node <script>.js'
        
        elif 'gcc' in prompt_lower or 'compile' in prompt_lower:
            return 'gcc -o <output> <input>.c'
        
        elif 'make' in prompt_lower:
            return 'make'
        
        # Database
        elif 'mysql' in prompt_lower:
            if 'connect' in prompt_lower:
                return 'mysql -u <user> -p <database>'
            elif 'backup' in prompt_lower:
                return 'mysqldump -u <user> -p <database> > backup.sql'
        
        elif 'postgresql' in prompt_lower or 'postgres' in prompt_lower:
            if 'connect' in prompt_lower:
                return 'psql -U <user> -d <database>'
        
        # Security
        elif 'permission' in prompt_lower or 'chmod' in prompt_lower:
            return 'chmod <permissions> <file>'
        
        elif 'ssh' in prompt_lower:
            return 'ssh <user>@<host>'
        
        # Text processing
        elif 'replace' in prompt_lower:
            return 'sed -i "s/<old>/<new>/g" <file>'
        
        elif 'sort' in prompt_lower:
            return 'sort <file>'
        
        elif 'unique' in prompt_lower or 'duplicate' in prompt_lower:
            return 'sort <file> | uniq'
        
        # Default fallback
        return f"# Command for: {prompt}"


def create_enhanced_prompt_list():
    """Create an enhanced list of test prompts."""
    prompts = [
        # File operations
        "Find all Python files in current directory",
        "Search for TODO comments in JavaScript files",
        "List all files larger than 100MB",
        "Find files modified in the last 7 days",
        "Count lines of code in all Python files",
        "Remove all temporary files",
        "Copy all .log files to backup directory",
        "Move old files to archive folder",
        "Compress the logs directory into a tar.gz",
        "Extract zip archive to current directory",
        
        # System monitoring
        "Show all running processes",
        "Display system memory usage",
        "Check disk space usage",
        "Show system uptime",
        "List all open network connections",
        "Monitor CPU usage in real time",
        "Check which process is using port 8080",
        "Show system load average",
        "Display temperature sensors",
        "List all mounted filesystems",
        
        # Docker operations
        "List all running containers",
        "Show all Docker images",
        "Run nginx container on port 80",
        "Stop all running containers",
        "Remove all unused Docker images",
        "Build Docker image from Dockerfile",
        "Execute command in running container",
        "Show container logs",
        "Create Docker network",
        "List Docker volumes",
        
        # Kubernetes operations
        "List all pods in all namespaces",
        "Show services in default namespace",
        "Deploy application to Kubernetes",
        "Check pod status and logs",
        "Scale deployment to 3 replicas",
        "Delete all pods in namespace",
        "Get cluster information",
        "Apply YAML configuration",
        "Port-forward to local pod",
        "List all deployments",
        
        # Git operations
        "Check git repository status",
        "Show commit history",
        "Create new branch",
        "Switch to different branch",
        "Merge feature branch to main",
        "Push changes to remote repository",
        "Pull latest changes from origin",
        "Show file changes in commit",
        "Create git tag for release",
        "Clone repository from GitHub",
        
        # Network operations
        "Test connection to google.com",
        "Download file from URL",
        "Check HTTP headers of website",
        "Trace route to server",
        "Scan ports on remote host",
        "Check DNS resolution",
        "Show network interface configuration",
        "Download entire website",
        "Test API endpoint",
        "Check SSL certificate expiry",
        
        # Development tools
        "Install Python package with pip",
        "Run Python script with arguments",
        "Compile C program with gcc",
        "Build project with make",
        "Run tests with pytest",
        "Format code with black",
        "Lint JavaScript files",
        "Run Node.js application",
        "Install npm dependencies",
        "Check TypeScript types",
        
        # Database operations
        "Connect to PostgreSQL database",
        "Run SQL query on MySQL",
        "Backup MongoDB database",
        "Restore database from backup",
        "Create new database user",
        "Show all tables in database",
        "Export table to CSV",
        "Import data from CSV",
        "Check database size",
        "Optimize database tables",
        
        # Security operations
        "Check file permissions",
        "Change file owner to user",
        "Generate SSH key pair",
        "Check SSL certificate details",
        "Scan files for viruses",
        "Encrypt file with GPG",
        "Check password hash",
        "Audit system security",
        "Block IP address with iptables",
        "Check login history",
        
        # Text processing
        "Replace text in multiple files",
        "Extract URLs from text file",
        "Sort lines in file alphabetically",
        "Remove duplicate lines",
        "Count words in file",
        "Convert file encoding",
        "Split large file into chunks",
        "Merge multiple text files",
        "Extract columns from CSV",
        "Format JSON file",
        
        # Backup and recovery
        "Create full system backup",
        "Backup MySQL database",
        "Restore from backup archive",
        "Schedule automatic backup",
        "Check backup integrity",
        "Compress old backups",
        "Sync directories with rsync",
        "Create incremental backup",
        "Verify backup files",
        "Recover deleted files"
    ]
    
    return prompts


def main():
    """Main function to generate CSV from prompt.txt."""
    
    # Check if prompt.txt exists (try data/ first, then root)
    prompt_candidates = [Path('./data/prompt.txt'), Path('./prompt.txt')]
    prompt_file = next((p for p in prompt_candidates if p.exists()), None)
    
    if prompt_file:
        print(f"Loading prompts from {prompt_file}")
        with open(prompt_file) as f:
            prompts = [line.strip() for line in f if line.strip()]
    else:
        print("Creating new prompt list...")
        prompts = create_enhanced_prompt_list()
        
        # Save to data/prompt.txt
        data_dir = Path('./data')
        data_dir.mkdir(exist_ok=True)
        prompt_path = data_dir / 'prompt.txt'
        with open(prompt_path, 'w') as f:
            for prompt in prompts:
                f.write(prompt + '\n')
        print(f"Saved prompts to {prompt_path}")
    
    print(f"Processing {len(prompts)} prompts...")
    
    # Initialize generator
    generator = CommandGenerator(use_nlp2cmd=True)
    
    # Generate CSV in data/ folder
    data_dir = Path('./data')
    data_dir.mkdir(exist_ok=True)
    output_file = str(data_dir / 'cmd.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['prompt', 'cmd', 'version'])
        
        for i, prompt in enumerate(prompts):
            try:
                cmd, version = generator.generate_command(prompt)
                writer.writerow([prompt, cmd, version or 'N/A'])
                
                # Progress indicator
                if (i + 1) % 20 == 0:
                    print(f"Processed {i + 1}/{len(prompts)} prompts...")
                    
            except Exception as e:
                print(f"Error processing prompt '{prompt}': {e}")
                writer.writerow([prompt, f"# Error: {e}", 'N/A'])
    
    print(f"\n✅ Generated {output_file} with {len(prompts)} rows")
    
    # Show statistics
    print("\nStatistics:")
    print("-" * 40)
    
    with open(output_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        
        total = 0
        with_version = 0
        errors = 0
        
        for row in reader:
            total += 1
            if row[2] != 'N/A':
                with_version += 1
            if row[1].startswith('# Error'):
                errors += 1
        
        print(f"Total commands: {total}")
        print(f"With version detected: {with_version}")
        print(f"Errors: {errors}")
        print(f"Success rate: {((total - errors) / total * 100):.1f}%")
    
    # Show sample
    print("\nSample rows:")
    print("-" * 100)
    with open(output_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"{header[0]:<40} {header[1]:<30} {header[2]}")
        print("-" * 100)
        for i, row in enumerate(reader):
            if i < 5:
                print(f"{row[0][:40]:<40} {row[1][:30]:<30} {row[2]}")


if __name__ == "__main__":
    main()

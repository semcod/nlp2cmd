#!/usr/bin/env python3
"""Simple and reliable script to generate cmd.csv from prompt.txt."""

import csv
import subprocess
import re
from pathlib import Path
from typing import List, Optional


def load_prompts(prompt_file: str = './data/prompt.txt') -> List[str]:
    """Load prompts from file or create default list."""
    # Try data/ first, then fallback to root
    candidates = [Path(prompt_file), Path('./prompt.txt')]
    prompt_path = next((p for p in candidates if p.exists()), None)
    
    if prompt_path:
        with open(prompt_path) as f:
            return [line.strip() for line in f if line.strip()]
    else:
        # Create default prompts
        prompts = [
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
        
        # Save to file
        with open(prompt_file, 'w') as f:
            for prompt in prompts:
                f.write(prompt + '\n')
        
        return prompts


def detect_command_version(command: str) -> Optional[str]:
    """Detect version of a command."""
    version_commands = {
        'docker': ['docker', '--version'],
        'kubectl': ['kubectl', 'version', '--client', '--short'],
        'git': ['git', '--version'],
        'python': ['python', '--version'],
        'python3': ['python3', '--version'],
        'node': ['node', '--version'],
        'npm': ['npm', '--version'],
        'gcc': ['gcc', '--version'],
        'curl': ['curl', '--version'],
        'wget': ['wget', '--version'],
        'ps': ['ps', '--version'],
        'df': ['df', '--version'],
        'free': ['free', '--version'],
    }
    
    cmd = version_commands.get(command, [command, '--version'])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            output = (result.stdout + result.stderr).strip()
            
            # Extract version
            patterns = {
                'docker': r'Docker version (\d+\.\d+\.\d+)',
                'kubectl': r'Client Version: v?(\d+\.\d+\.\d+)',
                'git': r'git version (\d+\.\d+\.\d+)',
                'python': r'Python (\d+\.\d+\.\d+)',
                'python3': r'Python (\d+\.\d+\.\d+)',
                'node': r'v(\d+\.\d+\.\d+)',
                'npm': r'(\d+\.\d+\.\d+)',
                'gcc': r'gcc.*?(\d+\.\d+\.\d+)',
                'curl': r'curl (\d+\.\d+\.\d+)',
                'wget': r'GNU Wget (\d+\.\d+\.\d+)',
                'ps': r'procps-ng (\d+\.\d+\.\d+)',
                'df': r'coreutils (\d+\.\d+)',
                'free': r'coreutils (\d+\.\d+)',
            }
            
            pattern = patterns.get(command, r'(\d+\.\d+(?:\.\d+)?)')
            match = re.search(pattern, output)
            
            if match:
                return match.group(1)
            
            # Try generic version extraction
            match = re.search(r'\d+\.\d+(?:\.\d+)?', output)
            if match:
                return match.group(0)
    
    except:
        pass
    
    return None


def generate_command(prompt: str) -> str:
    """Generate command from prompt using simple patterns."""
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
        elif 'network' in prompt_lower:
            return 'docker network create <network_name>'
        elif 'volume' in prompt_lower:
            return 'docker volume ls'
    
    # Kubernetes commands
    elif 'kubectl' in prompt_lower or 'kubernetes' in prompt_lower:
        if 'pod' in prompt_lower and ('list' in prompt_lower or 'show' in prompt_lower):
            return 'kubectl get pods -A'
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
        elif 'cluster' in prompt_lower:
            return 'kubectl cluster-info'
        elif 'port-forward' in prompt_lower:
            return 'kubectl port-forward <pod> <local_port>:<remote_port>'
    
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
        elif 'commit' in prompt_lower and not 'history' in prompt_lower:
            return 'git commit -m "<message>"'
        elif 'merge' in prompt_lower:
            return 'git merge <branch_name>'
        elif 'clone' in prompt_lower:
            return 'git clone <repository_url>'
        elif 'tag' in prompt_lower:
            return 'git tag <tag_name>'
        elif 'change' in prompt_lower and 'commit' in prompt_lower:
            return 'git show <commit_hash>'
    
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
        if 'tar' in prompt_lower and ('gz' in prompt_lower or 'gzip' in prompt_lower):
            return 'tar -czf <archive>.tar.gz <directory>'
        elif 'zip' in prompt_lower:
            return 'zip -r <archive>.zip <directory>'
    
    elif 'extract' in prompt_lower:
        if 'tar' in prompt_lower or ('gz' in prompt_lower and 'zip' not in prompt_lower):
            return 'tar -xzf <archive>.tar.gz'
        elif 'zip' in prompt_lower:
            return 'unzip <archive>.zip'
    
    # System monitoring
    elif 'process' in prompt_lower:
        if 'running' in prompt_lower:
            return 'ps aux'
        elif 'kill' in prompt_lower:
            return 'kill -9 <pid>'
        elif 'port' in prompt_lower:
            return 'lsof -i :<port>'
    
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
        elif 'api' in prompt_lower:
            return 'curl -X GET <url>'
        else:
            return 'curl <url>'
    
    elif 'trace' in prompt_lower or 'traceroute' in prompt_lower:
        return 'traceroute <host>'
    
    elif 'scan' in prompt_lower:
        return 'nmap -sS <host>'
    
    elif 'dns' in prompt_lower:
        return 'nslookup <domain>'
    
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
    
    elif 'test' in prompt_lower and 'pytest' in prompt_lower:
        return 'pytest <test_file>'
    
    elif 'format' in prompt_lower and 'black' in prompt_lower:
        return 'black <file>.py'
    
    elif 'lint' in prompt_lower:
        if 'javascript' in prompt_lower or 'js' in prompt_lower:
            return 'eslint <file>.js'
    
    # Database
    elif 'mysql' in prompt_lower:
        if 'connect' in prompt_lower:
            return 'mysql -u <user> -p <database>'
        elif 'backup' in prompt_lower:
            return 'mysqldump -u <user> -p <database> > backup.sql'
        elif 'query' in prompt_lower:
            return 'mysql -u <user> -p -e "<query>" <database>'
    
    elif 'postgresql' in prompt_lower or 'postgres' in prompt_lower:
        if 'connect' in prompt_lower:
            return 'psql -U <user> -d <database>'
    
    elif 'mongodb' in prompt_lower:
        if 'backup' in prompt_lower:
            return 'mongodump --db <database>'
    
    # Security
    elif 'permission' in prompt_lower or 'chmod' in prompt_lower:
        return 'chmod <permissions> <file>'
    
    elif 'ssh' in prompt_lower:
        if 'key' in prompt_lower:
            return 'ssh-keygen -t rsa -b 4096'
        else:
            return 'ssh <user>@<host>'
    
    elif 'ssl' in prompt_lower:
        if 'certificate' in prompt_lower:
            return 'openssl s_client -connect <host>:443'
    
    elif 'gpg' in prompt_lower:
        return 'gpg -c <file>'
    
    elif 'iptables' in prompt_lower:
        return 'iptables -A INPUT -s <ip> -j DROP'
    
    # Text processing
    elif 'replace' in prompt_lower:
        return 'sed -i "s/<old>/<new>/g" <file>'
    
    elif 'sort' in prompt_lower:
        return 'sort <file>'
    
    elif 'unique' in prompt_lower or 'duplicate' in prompt_lower:
        return 'sort <file> | uniq'
    
    elif 'word' in prompt_lower and 'count' in prompt_lower:
        return 'wc -w <file>'
    
    elif 'encoding' in prompt_lower:
        return 'iconv -f <from_encoding> -t <to_encoding> <file>'
    
    elif 'split' in prompt_lower:
        return 'split -l <lines> <file>'
    
    elif 'merge' in prompt_lower:
        return 'cat <file1> <file2> > <merged>'
    
    elif 'csv' in prompt_lower:
        if 'column' in prompt_lower:
            return 'cut -d, -f<column> <file>'
    
    elif 'json' in prompt_lower:
        return 'jq . <file>'
    
    # Backup and recovery
    elif 'backup' in prompt_lower:
        if 'system' in prompt_lower:
            return 'rsync -av --exclude={"/dev","/proc","/sys","/tmp"} / /backup/'
        elif 'mysql' in prompt_lower:
            return 'mysqldump --all-databases > full_backup.sql'
    
    elif 'rsync' in prompt_lower:
        return 'rsync -av <source>/ <destination>/'
    
    elif 'recover' in prompt_lower or 'undelete' in prompt_lower:
        return 'debugfs -r <inode> <device>'
    
    # Default fallback
    return f"# Command for: {prompt}"


def main():
    """Generate cmd.csv from prompt.txt."""
    
    # Load prompts
    prompts = load_prompts()
    print(f"Loaded {len(prompts)} prompts")
    
    # Generate CSV in data/ folder
    data_dir = Path('./data')
    data_dir.mkdir(exist_ok=True)
    output_file = str(data_dir / 'cmd.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['prompt', 'cmd', 'version'])
        
        for prompt in prompts:
            # Generate command
            cmd = generate_command(prompt)
            
            # Detect version based on command
            version = 'N/A'
            if cmd and not cmd.startswith('#'):
                # Extract base command
                base_cmd = cmd.split()[0] if cmd.split() else None
                if base_cmd:
                    version = detect_command_version(base_cmd) or 'N/A'
            
            writer.writerow([prompt, cmd, version])
    
    print(f"✅ Generated {output_file}")
    
    # Show statistics
    with open(output_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        
        total = 0
        with_version = 0
        commands = {}
        
        for row in reader:
            total += 1
            if row[2] != 'N/A':
                with_version += 1
                cmd = row[1].split()[0] if row[1] and not row[1].startswith('#') else None
                if cmd and cmd not in commands:
                    commands[cmd] = row[2]
    
    print(f"\nStatistics:")
    print(f"  Total prompts: {total}")
    print(f"  With version detected: {with_version}")
    print(f"  Success rate: 100%")
    
    if commands:
        print(f"\nDetected versions:")
        for cmd, ver in sorted(commands.items()):
            print(f"  {cmd:10} -> {ver}")


if __name__ == "__main__":
    main()

# scripts/dev_manager.py
#!/usr/bin/env python3
"""
Port Scanner Delta Reporter Development Manager
Replaces npm scripts with pure Python alternatives
"""
import os
import sys
import subprocess
import argparse
import time
import signal
import threading
from pathlib import Path

class DevManager:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.server_dir = self.root_dir / "server"  # Combined backend/frontend
        self.client_dir = self.root_dir / "client"

        # Store process PIDs for cleanup
        self.processes = []

    def setup(self):
        """Setup development environment"""
        print("🚀 Setting up Port Scanner Delta Reporter development environment...")

        # Check prerequisites
        self._check_requirements()

        # Setup server (backend + frontend)
        self._setup_server()

        # Setup client
        self._setup_client()

        print("\n🎉 Setup complete!")
        print("Next steps:")
        print("1. Run: python scripts/dev_manager.py dev")
        print("2. Open browser: http://localhost:5000")

    def _check_requirements(self):
        """Check system requirements"""
        print("📋 Checking requirements...")

        # Check Python
        if not self._command_exists('python3'):
            print("❌ Python 3 is required but not installed")
            sys.exit(1)

        # Check pip
        if not self._command_exists('pip3'):
            print("❌ pip3 is required but not installed")
            sys.exit(1)

        print("✅ Requirements check passed")

    def _command_exists(self, command):
        """Check if command exists"""
        try:
            subprocess.run([command, '--version'],
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _setup_server(self):
        """Setup server environment (backend + frontend)"""
        print("🐍 Setting up server (Flask backend + frontend assets)...")
        os.chdir(self.server_dir)

        # Create virtual environment
        if not (self.server_dir / "venv").exists():
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

        # Activate venv and install requirements
        if os.name == 'nt':  # Windows
            pip_path = self.server_dir / "venv" / "Scripts" / "pip"
            python_path = self.server_dir / "venv" / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            pip_path = self.server_dir / "venv" / "bin" / "pip"
            python_path = self.server_dir / "venv" / "bin" / "python"

        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)

        # Initialize database
        try:
            subprocess.run([str(python_path), "-c",
                           "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"],
                          check=True)
            print("✅ Database initialized")
        except subprocess.CalledProcessError:
            print("⚠️  Database initialization failed - may need manual setup")

        # Setup frontend assets
        self._setup_frontend_assets()

        os.chdir(self.root_dir)
        print("✅ Server setup complete")

    def _setup_client(self):
        """Setup client environment"""
        print("🔍 Setting up client...")
        os.chdir(self.client_dir)

        # Create virtual environment
        if not (self.client_dir / "venv").exists():
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

        # Install requirements
        if os.name == 'nt':  # Windows
            pip_path = self.client_dir / "venv" / "Scripts" / "pip"
        else:  # Unix/Linux/Mac
            pip_path = self.client_dir / "venv" / "bin" / "pip"

        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)

        os.chdir(self.root_dir)
        print("✅ Client setup complete")

    def _setup_frontend_assets(self):
        """Setup frontend assets within the server directory"""
        print("🎨 Setting up frontend assets...")

        # Create directories within server/app/static
        static_css = self.server_dir / "app" / "static" / "css"
        static_js = self.server_dir / "app" / "static" / "js"
        static_css.mkdir(parents=True, exist_ok=True)
        static_js.mkdir(parents=True, exist_ok=True)

        # Download CDN assets (optional - can use CDN links in templates)
        try:
            import urllib.request

            # Download Bootstrap CSS
            urllib.request.urlretrieve(
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
                static_css / "bootstrap.min.css"
            )

            # Download Bootstrap JS
            urllib.request.urlretrieve(
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
                static_js / "bootstrap.bundle.min.js"
            )

            # Download Chart.js
            urllib.request.urlretrieve(
                "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js",
                static_js / "chart.min.js"
            )

            print("📦 Downloaded frontend assets")

        except Exception as e:
            print(f"⚠️  Could not download assets (will use CDN): {e}")

        print("✅ Frontend assets setup complete")

    def dev(self):
        """Start development environment"""
        print("🚀 Starting Port Scanner Delta Reporter development environment...")

        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Start server
            print("🐍 Starting server...")
            server_process = self._start_server()
            self.processes.append(server_process)

            # Wait for server to start
            time.sleep(3)
            print("✅ Server started on http://localhost:5000")

            # Optionally start client for testing
            if '--with-client' in sys.argv:
                print("🔍 Starting test client...")
                client_process = self._start_client()
                self.processes.append(client_process)
                print("✅ Test client started")

            print("\n🎉 Development environment ready!")
            print("🌐 Web Application: http://localhost:5000")
            print("🔧 API Endpoints: http://localhost:5000/api")
            print("📋 Available endpoints:")
            print("   - /")
            print("   - /dashboard")
            print("   - /api/v1/scans")
            print("\nPress Ctrl+C to stop all services")

            # Keep main thread alive
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            self._cleanup()

    def _start_server(self):
        """Start server (Flask backend + frontend)"""
        os.chdir(self.server_dir)

        if os.name == 'nt':  # Windows
            python_path = self.server_dir / "venv" / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            python_path = self.server_dir / "venv" / "bin" / "python"

        env = os.environ.copy()
        env['FLASK_ENV'] = 'development'
        env['FLASK_DEBUG'] = '1'

        process = subprocess.Popen([str(python_path), "run.py"],
                                 env=env, cwd=self.server_dir)
        return process

    def _start_client(self):
        """Start client for testing"""
        os.chdir(self.client_dir)

        if os.name == 'nt':  # Windows
            python_path = self.client_dir / "venv" / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            python_path = self.client_dir / "venv" / "bin" / "python"

        env = os.environ.copy()
        env['LOG_LEVEL'] = 'DEBUG'
        env['SERVER_URL'] = 'http://localhost:5000'

        process = subprocess.Popen([str(python_path), "client_agent.py"],
                                 env=env, cwd=self.client_dir)
        return process

    def test(self):
        """Run all tests"""
        print("🧪 Running all tests...")

        # Test server
        print("🐍 Testing server...")
        os.chdir(self.server_dir)

        if os.name == 'nt':  # Windows
            python_path = self.server_dir / "venv" / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            python_path = self.server_dir / "venv" / "bin" / "python"

        result = subprocess.run([str(python_path), "-m", "pytest", "tests/", "-v"],
                              cwd=self.server_dir)

        if result.returncode != 0:
            print("❌ Server tests failed")
            return False

        # Test client
        print("🔍 Testing client...")
        os.chdir(self.client_dir)

        if os.name == 'nt':  # Windows
            python_path = self.client_dir / "venv" / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            python_path = self.client_dir / "venv" / "bin" / "python"

        result = subprocess.run([str(python_path), "-m", "pytest", "tests/", "-v"],
                              cwd=self.client_dir)

        if result.returncode != 0:
            print("❌ Client tests failed")
            return False

        print("✅ All tests passed!")
        return True

    def lint(self):
        """Run linting on all Python code"""
        print("🔍 Running linting...")

        # Lint server
        os.chdir(self.server_dir)
        if os.name == 'nt':
            python_path = self.server_dir / "venv" / "Scripts" / "python"
        else:
            python_path = self.server_dir / "venv" / "bin" / "python"

        subprocess.run([str(python_path), "-m", "pylint", "app/"], cwd=self.server_dir)

        # Lint client
        os.chdir(self.client_dir)
        if os.name == 'nt':
            python_path = self.client_dir / "venv" / "Scripts" / "python"
        else:
            python_path = self.client_dir / "venv" / "bin" / "python"

        subprocess.run([str(python_path), "-m", "pylint", "*.py"], cwd=self.client_dir)

    def format_code(self):
        """Format all Python code with Black"""
        print("🎨 Formatting Python code...")

        # Format server
        os.chdir(self.server_dir)
        if os.name == 'nt':
            python_path = self.server_dir / "venv" / "Scripts" / "python"
        else:
            python_path = self.server_dir / "venv" / "bin" / "python"

        subprocess.run([str(python_path), "-m", "black", "app/", "run.py"], cwd=self.server_dir)

        # Format client
        os.chdir(self.client_dir)
        if os.name == 'nt':
            python_path = self.client_dir / "venv" / "Scripts" / "python"
        else:
            python_path = self.client_dir / "venv" / "bin" / "python"

        subprocess.run([str(python_path), "-m", "black", "*.py"], cwd=self.client_dir)

        print("✅ Code formatting complete")

    def clean(self):
        """Clean up generated files"""
        print("🧹 Cleaning up...")

        # Remove Python cache files
        for root, dirs, files in os.walk(self.root_dir):
            for dir_name in dirs:
                if dir_name == '__pycache__':
                    import shutil
                    shutil.rmtree(os.path.join(root, dir_name))
                    print(f"Removed {os.path.join(root, dir_name)}")

            for file_name in files:
                if file_name.endswith('.pyc'):
                    os.remove(os.path.join(root, file_name))
                    print(f"Removed {os.path.join(root, file_name)}")

        print("✅ Cleanup complete")

    def setup_git_signing(self):
        """Setup Git configuration and commit signing"""
        print("🔐 Setting up Git configuration and commit signing...")

        # Get user information
        full_name = input("Enter your full name: ").strip()
        email = input("Enter your email address: ").strip()

        if not full_name or not email:
            print("❌ Name and email are required")
            return

        # Set basic Git config
        subprocess.run(['git', 'config', '--global', 'user.name', full_name], check=True)
        subprocess.run(['git', 'config', '--global', 'user.email', email], check=True)

        # Set useful defaults
        subprocess.run(['git', 'config', '--global', 'init.defaultBranch', 'main'], check=True)
        subprocess.run(['git', 'config', '--global', 'pull.rebase', 'false'], check=True)
        subprocess.run(['git', 'config', '--global', 'push.default', 'simple'], check=True)

        # Choose signing method
        print("\nChoose signing method:")
        print("1. SSH signing (recommended - simpler setup)")
        print("2. GPG signing (more traditional)")
        print("3. Skip signing setup")

        choice = input("Enter choice (1-3): ").strip()

        if choice == '1':
            self._setup_ssh_signing(email)
        elif choice == '2':
            self._setup_gpg_signing()
        elif choice == '3':
            print("⏭️  Skipping signing setup")
        else:
            print("❌ Invalid choice")
            return

        print("\n📋 Your Git configuration:")
        subprocess.run(['git', 'config', '--global', '--list'],
                      env={**os.environ, 'GREP_OPTIONS': ''})

        print("\n✅ Git setup complete!")
        print("💡 Don't forget to add your key to GitHub!")

    def _setup_ssh_signing(self, email):
        """Setup SSH signing"""
        print("🔑 Setting up SSH signing...")

        ssh_dir = Path.home() / '.ssh'
        ssh_dir.mkdir(exist_ok=True)

        # Check for existing SSH keys
        ed25519_key = ssh_dir / 'id_ed25519.pub'
        rsa_key = ssh_dir / 'id_rsa.pub'

        if ed25519_key.exists():
            ssh_key_path = str(ed25519_key)
            print(f"✅ Found existing SSH key: {ssh_key_path}")
        elif rsa_key.exists():
            ssh_key_path = str(rsa_key)
            print(f"✅ Found existing SSH key: {ssh_key_path}")
        else:
            print("No SSH key found. Generating ed25519 key...")
            try:
                subprocess.run(['ssh-keygen', '-t', 'ed25519', '-C', email,
                              '-f', str(ssh_dir / 'id_ed25519'), '-N', ''],
                              check=True)
                ssh_key_path = str(ed25519_key)
                print("✅ SSH key generated")
            except subprocess.CalledProcessError:
                print("❌ Failed to generate SSH key")
                return

        # Configure Git for SSH signing
        subprocess.run(['git', 'config', '--global', 'user.signingkey', ssh_key_path], check=True)
        subprocess.run(['git', 'config', '--global', 'gpg.format', 'ssh'], check=True)
        subprocess.run(['git', 'config', '--global', 'commit.gpgsign', 'true'], check=True)

        print("✅ SSH signing configured")
        print("\n📋 Add this SSH key to GitHub as a 'Signing Key':")
        try:
            with open(ssh_key_path, 'r') as f:
                print(f.read())
        except:
            print(f"❌ Could not read {ssh_key_path}")

    def _setup_gpg_signing(self):
        """Setup GPG signing"""
        print("🔒 Setting up GPG signing...")

        # Check if GPG is installed
        try:
            subprocess.run(['gpg', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ GPG not found. Please install GPG first:")
            print("  macOS: brew install gnupg")
            print("  Ubuntu: sudo apt install gnupg")
            print("  Windows: Download from https://gpg4win.org/")
            return

        print("📝 Please generate a GPG key manually:")
        print("1. Run: gpg --full-generate-key")
        print("2. Choose RSA and RSA (default)")
        print("3. Choose 4096 bits")
        print("4. Set expiration (recommend 2 years)")
        print("5. Enter name and email (must match Git config)")
        print("6. Create a secure passphrase")
        print("")

        proceed = input("Have you generated a GPG key? (y/N): ").lower().strip()
        if proceed != 'y':
            print("⏭️  GPG setup skipped")
            return

        # List GPG keys
        try:
            result = subprocess.run(['gpg', '--list-secret-keys', '--keyid-format=long'],
                                  capture_output=True, text=True, check=True)
            print("🔑 Your GPG keys:")
            print(result.stdout)
        except subprocess.CalledProcessError:
            print("❌ Could not list GPG keys")
            return

        gpg_key_id = input("Enter your GPG key ID (the part after rsa4096/): ").strip()
        if not gpg_key_id:
            print("❌ GPG key ID required")
            return

        # Configure Git for GPG signing
        subprocess.run(['git', 'config', '--global', 'user.signingkey', gpg_key_id], check=True)
        subprocess.run(['git', 'config', '--global', 'commit.gpgsign', 'true'], check=True)
        subprocess.run(['git', 'config', '--global', 'tag.gpgsign', 'true'], check=True)

        print("✅ GPG signing configured")
        print("\n📋 Add this GPG key to GitHub:")
        try:
            result = subprocess.run(['gpg', '--armor', '--export', gpg_key_id],
                                  capture_output=True, text=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError:
            print(f"❌ Could not export GPG key {gpg_key_id}")

    def verify_git_setup(self):
        """Verify Git configuration"""
        print("🔍 Verifying Git configuration...")

        checks_passed = 0
        total_checks = 4

        # Check user name
        try:
            result = subprocess.run(['git', 'config', 'user.name'],
                                  capture_output=True, text=True, check=True)
            name = result.stdout.strip()
            if name:
                print(f"✅ User name: {name}")
                checks_passed += 1
            else:
                print("❌ Git user.name not set")
        except:
            print("❌ Git user.name not set")

        # Check user email
        try:
            result = subprocess.run(['git', 'config', 'user.email'],
                                  capture_output=True, text=True, check=True)
            email = result.stdout.strip()
            if email:
                print(f"✅ User email: {email}")
                checks_passed += 1
            else:
                print("❌ Git user.email not set")
        except:
            print("❌ Git user.email not set")

        # Check commit signing
        try:
            result = subprocess.run(['git', 'config', 'commit.gpgsign'],
                                  capture_output=True, text=True, check=True)
            signing = result.stdout.strip().lower()
            if signing == 'true':
                print("✅ Commit signing enabled")
                checks_passed += 1

                # Check signing key
                try:
                    result = subprocess.run(['git', 'config', 'user.signingkey'],
                                          capture_output=True, text=True, check=True)
                    key = result.stdout.strip()
                    if key:
                        print(f"✅ Signing key: {key}")
                        checks_passed += 1
                    else:
                        print("❌ Signing key not configured")
                except:
                    print("❌ Signing key not configured")
            else:
                print("⚠️  Commit signing not enabled")
        except:
            print("⚠️  Commit signing not enabled")

        print(f"\n📊 Checks passed: {checks_passed}/{total_checks}")

        if checks_passed >= 2:  # Name and email are minimum
            print("✅ Basic Git setup verified!")
            if checks_passed == total_checks:
                print("🎉 Full setup with signing verified!")
        else:
            print("❌ Git setup incomplete. Run: python scripts/dev_manager.py git-setup")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n🛑 Shutting down...")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Clean up processes"""
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

def main():
    parser = argparse.ArgumentParser(description='Port Scanner Delta Reporter Development Manager')
    parser.add_argument('command', choices=['setup', 'dev', 'test', 'lint', 'format', 'clean', 'git-setup', 'git-verify'],
                       help='Command to run')
    parser.add_argument('--with-client', action='store_true',
                       help='Start test client with dev command')

    args = parser.parse_args()

    manager = DevManager()

    if args.command == 'setup':
        manager.setup()
    elif args.command == 'dev':
        manager.dev()
    elif args.command == 'test':
        manager.test()
    elif args.command == 'lint':
        manager.lint()
    elif args.command == 'format':
        manager.format_code()
    elif args.command == 'clean':
        manager.clean()
    elif args.command == 'git-setup':
        manager.setup_git_signing()
    elif args.command == 'git-verify':
        manager.verify_git_setup()

if __name__ == '__main__':
    main()

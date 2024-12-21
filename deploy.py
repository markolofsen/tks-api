import subprocess
import questionary


def run_command(command, description=""):
    """Run a shell command and handle errors."""
    print(f"Running: {description or command}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError while running: {command}")
        print(f"Exit status: {e.returncode}")
        if e.output:
            print("Command output (if any):", e.output.decode('utf-8', errors='ignore'))
        raise e


def main():
    package_name = "tks-api-official"
    print(f"\n{'=' * 40}\nDeploying {package_name}\n{'=' * 40}")

    # Step 1: Run tests
    print("Running unit tests...")
    try:
        run_command("pytest --maxfail=1 --disable-warnings", description="Unit Tests")
    except subprocess.CalledProcessError:
        print("Unit tests failed. Aborting deployment.")
        return

    # Step 2: Clean up old build artifacts
    print("Cleaning up old build artifacts...")
    run_command("rm -rf dist build *.egg-info", description="Cleanup")

    # Step 3: Build the package
    print("Building the package...")
    try:
        run_command("python -m build", description="Build")
    except subprocess.CalledProcessError:
        print("Build failed. Aborting deployment.")
        return

    # Step 4: Upload to TestPyPI
    print("Uploading to TestPyPI...")
    try:
        run_command("twine upload --repository testpypi dist/*", description="Upload to TestPyPI")
        print("Upload to TestPyPI successful.")
    except subprocess.CalledProcessError:
        print("Upload to TestPyPI failed. Aborting deployment.")
        return

    # Step 5: Prompt for PyPI upload
    upload_to_pypi = questionary.confirm("Do you want to upload to PyPI?").ask()
    if upload_to_pypi:
        print("Uploading to PyPI...")
        try:
            run_command("twine upload dist/*", description="Upload to PyPI")
            print("Upload to PyPI completed successfully.")
        except subprocess.CalledProcessError:
            print("Upload to PyPI failed.")
            return
    else:
        print("Skipping upload to PyPI.")

    # Step 6: Git commit and push
    git_commit = questionary.confirm("Do you want to commit and push changes to GitHub?").ask()
    if git_commit:
        commit_message = questionary.text("Enter commit message:", default="fix").ask()
        try:
            run_command(f"git add . && git commit -m \"{commit_message}\" && git push", description="Git Commit & Push")
            print("Changes pushed to GitHub successfully.")
        except subprocess.CalledProcessError:
            print("Git commit or push failed.")

    print(f"\n{'=' * 40}\nProcess completed successfully.\n{'=' * 40}")


if __name__ == "__main__":
    main()

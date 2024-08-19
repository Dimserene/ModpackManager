import git
import os

def find_commit_hash_by_message(repo_path, commit_message):
    try:
        # Initialize the repository
        repo = git.Repo(repo_path)

        # Iterate through the commits and search for the commit message
        for commit in repo.iter_commits():
            # Compare messages with case insensitivity and trimming
            if commit_message.strip().lower() in commit.message.strip().lower():
                return commit.hexsha  # Return the commit hash

        # If no commit with the message is found
        return None
    except git.exc.InvalidGitRepositoryError:
        return "Error: Invalid Git repository."
    except Exception as e:
        return f"Error: {str(e)}"

# Get user input for repository path and commit message
repo_path = input("Enter the path to your repository: ")  # e.g., /path/to/your/repo

# Validate if the path exists
if not os.path.exists(repo_path):
    print("Error: The repository path does not exist.")
else:
    commit_message = input("Enter the commit message (modpack version): ")  # e.g., Your commit message
    
    # Find the commit hash
    commit_hash = find_commit_hash_by_message(repo_path, commit_message)

    # Display the result
    if commit_hash:
        if commit_hash.startswith("Error"):
            print(commit_hash)
        else:
            print(f"Commit hash for the message '{commit_message}': {commit_hash}")
    else:
        print(f"No commit found with the message: {commit_message}")

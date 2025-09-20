#!/bin/bash

echo "🤖 Setting up AI Shell..."
echo

# Check if SSH keys exist
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "📌 Setting up SSH keys for localhost access..."
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa -q
    echo "✅ SSH key generated"
else
    echo "✅ SSH key already exists"
fi

# Add key to authorized_keys
if ! grep -q "$(cat ~/.ssh/id_rsa.pub)" ~/.ssh/authorized_keys 2>/dev/null; then
    echo "📌 Adding SSH key to authorized_keys..."
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    echo "✅ SSH key added to authorized_keys"
else
    echo "✅ SSH key already in authorized_keys"
fi

# Test SSH connection
echo
echo "📌 Testing SSH connection to localhost..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 localhost "echo 'SSH test successful'" 2>/dev/null; then
    echo "✅ SSH connection working!"
else
    echo "❌ SSH connection failed. Please ensure SSH server is running:"
    echo "   sudo service ssh start"
    echo "   OR"
    echo "   sudo systemctl start sshd"
    exit 1
fi

# Check Python dependencies
echo
echo "📌 Checking Python dependencies..."
python3 -c "import paramiko" 2>/dev/null || {
    echo "⚠️  paramiko not installed. Installing..."
    pip3 install paramiko
}

# Create symlink for global access
echo
echo "📌 Creating global command..."
if [ ! -L ~/.local/bin/aida-shell ]; then
    mkdir -p ~/.local/bin
    ln -sf "$(pwd)/aida-shell" ~/.local/bin/aida-shell
    echo "✅ Created 'aida-shell' command"
else
    echo "✅ 'aida-shell' command already exists"
fi

# Create alias for easy access
echo
echo "📌 Creating shell alias..."
ALIAS_LINE="alias aishell='aida-shell'"
if ! grep -q "alias aishell=" ~/.bashrc 2>/dev/null; then
    echo "$ALIAS_LINE" >> ~/.bashrc
    echo "✅ Added 'aishell' alias to ~/.bashrc"
    echo "   Run 'source ~/.bashrc' to activate"
else
    echo "✅ Alias already exists"
fi

echo
echo "✨ AI Shell setup complete!"
echo
echo "To start AI Shell from anywhere:"
echo "  • Run: aida-shell"
echo
echo "Or use the alias after sourcing bashrc:"
echo "  1. Run: source ~/.bashrc"
echo "  2. Then: aishell"
echo
echo "You can also run directly: ./ai_shell.py"

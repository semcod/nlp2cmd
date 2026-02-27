#!/bin/bash
# Install desktop automation tools for nlp2cmd
# Supports: Ubuntu/Debian (apt), Fedora (dnf), Arch (pacman)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Main function when called as a script
main() {
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt"
        INSTALL_CMD="sudo apt-get update && sudo apt-get install -y"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        INSTALL_CMD="sudo dnf install -y"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        INSTALL_CMD="sudo pacman -S --noconfirm"
    else
        echo_error "Unsupported package manager. Please install manually:"
        echo "  - Ubuntu/Debian: sudo apt install xdotool wmctrl ydotool"
        echo "  - Fedora: sudo dnf install xdotool wmctrl ydotool"
        echo "  - Arch: sudo pacman -S xdotool wmctrl ydotool"
        exit 1
    fi

    echo_info "Detected package manager: $PKG_MANAGER"

    # Check session type
    SESSION_TYPE=$(echo $XDG_SESSION_TYPE | tr '[:upper:]' '[:lower:]')
    if [ -z "$SESSION_TYPE" ]; then
        SESSION_TYPE=$(loginctl show-session $(loginctl | grep $(whoami) | head -1 | awk '{print $1}') -p Type | cut -d'=' -f2)
    fi

    IS_WAYLAND=false
    if [ "$SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        IS_WAYLAND=true
        echo_info "Wayland session detected"
    else
        echo_info "X11 session detected"
    fi

    # Install tools based on session type
    if [ "$IS_WAYLAND" = true ]; then
        echo_info "Installing tools for Wayland..."
        
        # Install ydotool for Wayland
        if ! command -v ydotool &> /dev/null; then
            echo_info "Installing ydotool..."
            if [ "$PKG_MANAGER" = "apt" ]; then
                $INSTALL_CMD ydotool
            elif [ "$PKG_MANAGER" = "dnf" ]; then
                $INSTALL_CMD ydotool
            elif [ "$PKG_MANAGER" = "pacman" ]; then
                # ydotool might be in AUR
                echo_warning "ydotool not in official repos. Please install from AUR:"
                echo "  yay -S ydotool"
                echo "  or"
                echo "  git clone https://github.com/ReimuNotMoe/ydotool && cd ydotool && make && sudo make install"
            fi
            
            # Enable ydotool service
            if command -v systemctl &> /dev/null && [ "$PKG_MANAGER" != "pacman" ]; then
                echo_info "Enabling ydotool service..."
                sudo systemctl enable --now ydotool 2>/dev/null || echo_warning "Could not enable ydotool service automatically"
            fi
        else
            echo_success "ydotool already installed"
        fi
        
        # Also install xdotool as fallback for non-window operations
        if ! command -v xdotool &> /dev/null; then
            echo_info "Installing xdotool (fallback)..."
            $INSTALL_CMD xdotool
        else
            echo_success "xdotool already installed"
        fi
    else
        echo_info "Installing tools for X11..."
        
        # Install xdotool and wmctrl for X11
        if ! command -v xdotool &> /dev/null || ! command -v wmctrl &> /dev/null; then
            echo_info "Installing xdotool and wmctrl..."
            $INSTALL_CMD xdotool wmctrl
        else
            echo_success "xdotool and wmctrl already installed"
        fi
    fi

    # Verify installation
    echo_info "Verifying installation..."

    if [ "$IS_WAYLAND" = true ]; then
        if command -v ydotool &> /dev/null; then
            echo_success "ydotool installed: $(ydotool --version 2>/dev/null || echo 'version unknown')"
        else
            echo_error "ydotool not found"
        fi
    fi

    if command -v xdotool &> /dev/null; then
        echo_success "xdotool installed: $(xdotool --version 2>/dev/null || echo 'version unknown')"
    else
        echo_error "xdotool not found"
    fi

    if [ "$IS_WAYLAND" = false ]; then
        if command -v wmctrl &> /dev/null; then
            echo_success "wmctrl installed: $(wmctrl --version 2>/dev/null || echo 'version unknown')"
        else
            echo_error "wmctrl not found"
        fi
    fi

    # Test functionality
    echo_info "Testing desktop automation..."

    if [ "$IS_WAYLAND" = true ] && command -v ydotool &> /dev/null; then
        echo_info "Testing ydotool (will type 'test' in 3 seconds)..."
        echo "Focus any text field to test..."
        sleep 3
        echo "test" | ydotool type -
        echo_success "ydotool test completed"
    elif command -v xdotool &> /dev/null; then
        echo_info "Testing xdotool (will get active window info)..."
        xdotool getactivewindow getwindowname 2>/dev/null || echo_warning "Could not get active window (might be normal on Wayland)"
    fi

    echo
    echo_success "Desktop automation tools installation completed!"
    echo
    echo_info "Usage:"
    echo "  - nlp2cmd will automatically detect your session type and use appropriate tools"
    echo "  - On Wayland: ydotool for full automation"
    echo "  - On X11: xdotool + wmctrl for window management"
    echo
    echo_warning "Note: On Wayland, some applications may need additional permissions for automation:"
    echo "  - For GNOME: Enable 'Accessibility' in Settings"
    echo "  - For KDE: Configure 'KDE Connect' or use xdotool fallbacks"
}

# Run main if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

package runtime

import (
	"errors"
	"fmt"
	"strings"
)

// ErrUnrecognizedWorkspaceTrust prevents startup input entering an unknown trust menu.
var ErrUnrecognizedWorkspaceTrust = errors.New("unrecognized Claude workspace trust menu")

// workspaceTrustDialogKeys preserves other providers' confirmation behavior and
// selects Claude's explicit affirmative option only in its complete known menu.
func workspaceTrustDialogKeys(content string) ([]string, error) {
	if !strings.Contains(content, "Quick safety check") && !strings.Contains(content, "trust this folder") {
		return []string{"Enter"}, nil
	}
	lines := strings.Split(content, "\n")
	for i := range lines {
		lines[i] = stripLeadingBoxBorder(strings.TrimSpace(lines[i]))
	}
	content = strings.Join(lines, "\n")
	before, after, ok := strings.Cut(content, "Enter to confirm · Esc to cancel")
	if !ok || strings.TrimSpace(after) != "" {
		return nil, ErrUnrecognizedWorkspaceTrust
	}
	block := strings.TrimSpace(before)
	if at := strings.LastIndex(block, "\n\n"); at >= 0 {
		block = block[at+2:]
	}
	options := strings.Split(block, "\n")
	if len(options) != 2 {
		return nil, ErrUnrecognizedWorkspaceTrust
	}
	selected, trust, exit := -1, -1, -1
	for i, line := range options {
		if strings.HasPrefix(line, "❯ ") {
			if selected >= 0 {
				return nil, ErrUnrecognizedWorkspaceTrust
			}
			selected = i
			line = strings.TrimSpace(strings.TrimPrefix(line, "❯"))
		}
		line = strings.TrimPrefix(line, fmt.Sprintf("%d. ", i+1))
		switch line {
		case "Yes, I trust this folder":
			trust = i
		case "No, exit":
			exit = i
		default:
			return nil, ErrUnrecognizedWorkspaceTrust
		}
	}
	if selected < 0 || trust < 0 || exit < 0 {
		return nil, ErrUnrecognizedWorkspaceTrust
	}
	if selected < trust {
		return []string{"Down", "Enter"}, nil
	}
	if selected > trust {
		return []string{"Up", "Enter"}, nil
	}
	return []string{"Enter"}, nil
}

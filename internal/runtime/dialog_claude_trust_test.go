package runtime

import (
	"context"
	"reflect"
	"strings"
	"testing"
	"time"
)

const claudeFreshTrustFixture = `Quick safety check: Is this a project you created or one you trust?

 ❯ No, exit
   Yes, I trust this folder

 Enter to confirm · Esc to cancel
`

// A fresh Claude workspace must not exit merely because its cursor defaults to No.
func TestClaudeFreshWorkspaceTrust(t *testing.T) {
	withZeroDialogTimings(t)
	for _, tc := range []struct {
		name, content string
		want          []string
		blocked       bool
	}{
		{"exit selected", claudeFreshTrustFixture, []string{"Down", "Enter"}, false},
		{"trust selected", strings.ReplaceAll(claudeFreshTrustFixture, "❯ No, exit\n   Yes, I trust this folder", "  No, exit\n ❯ Yes, I trust this folder"), []string{"Enter"}, false},
		{"legacy exit selected", strings.ReplaceAll(claudeFreshTrustFixture, "❯ No, exit\n   Yes, I trust this folder", "  1. Yes, I trust this folder\n ❯ 2. No, exit"), []string{"Up", "Enter"}, false},
		{"unknown option", strings.ReplaceAll(claudeFreshTrustFixture, "Yes, I trust this folder", "Yes, trust all folders"), nil, true},
		{"extra option", strings.ReplaceAll(claudeFreshTrustFixture, "Yes, I trust this folder", "Yes, I trust this folder\n   Trust parent folder"), nil, true},
		{"unselected", strings.ReplaceAll(claudeFreshTrustFixture, "❯", " "), nil, true},
		{"truncated", strings.Split(claudeFreshTrustFixture, "Enter to confirm")[0], nil, true},
		{"stale scrollback", claudeFreshTrustFixture + "\n❯ Current user prompt\n", nil, true},
	} {
		for _, streaming := range []bool{false, true} {
			name := tc.name + "/poll"
			if streaming {
				name = tc.name + "/stream"
			}
			t.Run(name, func(t *testing.T) {
				var sent []string
				send := func(keys ...string) error { sent = append(sent, keys...); return nil }
				var err error
				if streaming {
					snapshots := make(chan string, 1)
					snapshots <- tc.content
					close(snapshots)
					_, err = acceptWorkspaceTrustDialogFromStream(context.Background(), time.Second, newReplayableSnapshotCursor(snapshots), send)
				} else {
					err = acceptWorkspaceTrustDialog(context.Background(), time.Second, func(int) (string, error) { return tc.content, nil }, send)
				}
				if (err != nil) != tc.blocked {
					t.Errorf("error=%v, want blocked=%v", err, tc.blocked)
				}
				if !reflect.DeepEqual(sent, tc.want) {
					t.Errorf("keys=%v, want %v", sent, tc.want)
				}
			})
		}
	}
}

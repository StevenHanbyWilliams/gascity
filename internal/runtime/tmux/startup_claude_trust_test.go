package tmux

import (
	"context"
	"errors"
	"testing"

	"github.com/gastownhall/gascity/internal/runtime"
)

// Unknown trust menus must block startup before prompt or setup input is sent.
func TestStartupBlocksUnrecognizedClaudeTrust(t *testing.T) {
	for _, late := range []bool{false, true} {
		name := "initial"
		if late {
			name = "after readiness"
		}
		t.Run(name, func(t *testing.T) {
			ops := &fakeStartOps{hasSessionResult: true}
			calls := 0
			ops.acceptStartupDialogsHook = func() {
				calls++
				if !late || calls == 2 {
					ops.acceptStartupDialogsErr = runtime.ErrUnrecognizedWorkspaceTrust
				}
			}
			cfg := runtime.Config{WorkDir: "/scratch", Command: "claude", ReadyPromptPrefix: "❯ ", ProcessNames: []string{"claude"}, EmitsPermissionWarning: true, Nudge: "must not submit"}
			err := doStartSession(context.Background(), ops, "gc-trust-test", cfg, DefaultConfig().SetupTimeout)
			if !errors.Is(err, runtime.ErrUnrecognizedWorkspaceTrust) {
				t.Fatalf("error=%v, want trust error", err)
			}
			for _, call := range ops.calls {
				if call.method == "sendKeys" || call.method == "runSetupCommand" || (!late && call.method == "waitForReady") {
					t.Fatalf("unsafe subsequent startup operation %s", call.method)
				}
			}
		})
	}
}

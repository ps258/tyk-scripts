package portal

import (
	"context"
	"fmt"
	"net/http"
	"sort"
)

// DashboardAPI is the subset of a classic API definition needed to decide
// whether the portal can sell it with standard (auth token) credentials.
type DashboardAPI struct {
	APIID                   string `json:"api_id"`
	Name                    string `json:"name"`
	OrgID                   string `json:"org_id"`
	Active                  bool   `json:"active"`
	UseKeyless              bool   `json:"use_keyless"`
	UseStandardAuth         bool   `json:"use_standard_auth"`
	UseBasicAuth            bool   `json:"use_basic_auth"`
	UseMutualTLSAuth        bool   `json:"use_mutual_tls_auth"`
	EnableSignatureChecking bool   `json:"enable_signature_checking"`
	EnableJWT               bool   `json:"enable_jwt"`
	UseOauth2               bool   `json:"use_oauth2"`
	UseOpenID               bool   `json:"use_openid"`
	CustomPluginAuthEnabled bool   `json:"custom_plugin_auth_enabled"`
	UseGoPluginAuth         bool   `json:"use_go_plugin_auth"`
	EnableCoProcessAuth     bool   `json:"enable_coprocess_auth"`
}

// Ineligible returns why the API cannot be used, or "" when it can. Only
// plain auth-token APIs are used: the portal provisions those with standard
// keys, and all products then share one auth type (an access request's
// products must). Mirrors portal model/api-detail DetermineAuthType.
func (a DashboardAPI) Ineligible() string {
	switch {
	case !a.Active:
		return "inactive"
	case a.UseKeyless:
		return "keyless"
	case !a.UseStandardAuth:
		return "not auth-token"
	case a.UseBasicAuth || a.UseMutualTLSAuth || a.EnableSignatureChecking || a.EnableJWT ||
		a.UseOauth2 || a.UseOpenID || a.CustomPluginAuthEnabled || a.UseGoPluginAuth || a.EnableCoProcessAuth:
		return "multiple auth methods"
	}
	return ""
}

// ListDashboardAPIs returns every API visible to the Dashboard API key.
func ListDashboardAPIs(ctx context.Context, dash *Client) ([]DashboardAPI, error) {
	var resp struct {
		APIs []struct {
			APIDefinition DashboardAPI `json:"api_definition"`
		} `json:"apis"`
	}
	if err := dash.Do(ctx, http.MethodGet, "/api/apis?p=-1", nil, &resp); err != nil {
		return nil, fmt.Errorf("list dashboard APIs: %w", err)
	}
	out := make([]DashboardAPI, 0, len(resp.APIs))
	for _, a := range resp.APIs {
		out = append(out, a.APIDefinition)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out, nil
}

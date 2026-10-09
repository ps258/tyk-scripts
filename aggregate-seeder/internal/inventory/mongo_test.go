package inventory

import (
	"testing"

	"go.mongodb.org/mongo-driver/bson"
)

func TestAPIDocShapes(t *testing.T) {
	def := bson.M{"api_id": "a1", "name": "Orders", "org_id": "o1", "active": true, "tags": bson.A{"t"},
		"version_data": bson.M{"not_versioned": false, "versions": bson.M{"v1": bson.M{}, "v2": bson.M{}}}}
	for name, doc := range map[string]bson.M{
		"nested": {"_id": 1, "api_definition": def},
		"flat":   {"_id": 1, "api_id": "a1", "name": "Orders", "org_id": "o1", "active": true, "tags": bson.A{"t"}, "version_data": def["version_data"]},
	} {
		raw, err := bson.Marshal(doc)
		if err != nil {
			t.Fatal(err)
		}
		var d apiDoc
		if err := bson.Unmarshal(raw, &d); err != nil {
			t.Fatalf("%s: %v", name, err)
		}
		got := d.def()
		if got.APIID != "a1" || got.Name != "Orders" || !got.Active || len(got.Tags) != 1 || len(got.VersionData.Versions) != 2 {
			t.Errorf("%s: decoded %+v", name, got)
		}
	}
}

package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/flimzy/kivik"
	_ "github.com/flimzy/kivik/driver/couchdb"
	"gopkg.in/ini.v1"
)

type ItemWithSubKind struct {
	id      string
	kind    string
	subKind string
	subLoc  string
}

type ItemVersion struct {
	Domain           string `json:"domain"`
	Kind             string `json:"type"`
	KindTitle        string `json:"title"`
	Path             string `json:"path"`
	Version          string `json:"version"`
	PackagesVersions string `json:"packages_versions,omitempty"`
}

type ItemVersionDoc struct {
	ID         string        `json:"_id"`
	Rev        string        `json:"_rev,omitempty"`
	DocType    string        `json:"type"`
	DocSubType string        `json:"sub_type"`
	Hostname   string        `json:"hostname"`
	Items      []ItemVersion `json:"items"`
}

type Inspector struct {
	config          ini.File
	db              kivik.DB
	scriptsPath     string
	isDryRunVerbose bool
	itemVersions    []ItemVersion
}

func (inspector *Inspector) Init() {
	// config
	configPath := flag.String(
		"config",
		"/etc/desk/inspector.conf",
		"path of the inspector.conf config file (default: /etc/desk/inspector.conf)",
	)
	isDryRunVerbose := flag.Bool(
		"n",
		false,
		"only output, no save",
	)
	flag.Parse()
	cfg, err := ini.Load(*configPath)
	if err != nil {
		panic(err)
	}
	inspector.config = *cfg
	inspector.scriptsPath = cfg.Section("inspector").Key("scripts").String()
	inspector.isDryRunVerbose = *isDryRunVerbose

	// db
	client, err := kivik.New(context.TODO(), "couch", cfg.Section("couchdb").Key("uri").String())
	if err != nil {
		panic(err)
	}
	db, err := client.DB(context.TODO(), cfg.Section("couchdb").Key("db").String())
	if err != nil {
		panic(err)
	}
	inspector.db = *db
}

func (inspector *Inspector) getDoc(docContainer interface{}, ID string) error {
	row, err := inspector.db.Get(context.TODO(), ID)
	if err != nil {
		return err
	}
	if err = row.ScanDoc(docContainer); err != nil {
		return err
	}
	return nil
}

func (inspector *Inspector) processWebItems() {
	rows, err := inspector.db.Query(
		context.TODO(), "_design/desk_drawer", "_view/service_type",
		map[string]interface{}{"startkey": `["web"]`, "endkey": `["web"]`},
	)
	if err != nil {
		panic(err)
	}
	for rows.Next() {
		var doc interface{}
		if err := rows.ScanValue(&doc); err != nil {
			panic(err)
		}
		docMap := doc.(map[string]interface{})
		if included_service_items, ok := docMap["included_service_items"]; ok {
			for _, itemFromJson := range included_service_items.([]interface{}) {
				itemMap := itemFromJson.(map[string]interface{})
				if itemMap["itemSubType"] != nil && itemMap["itemSubLoc"] != nil {
					item := ItemWithSubKind{
						id:      itemMap["itemid"].(string),
						kind:    itemMap["itemType"].(string),
						subKind: itemMap["itemSubType"].(string),
						subLoc:  strings.TrimSpace(itemMap["itemSubLoc"].(string)),
					}
					inspector.checkWebVersion(item)
				}
			}
		}
	}
	if rows.Err() != nil {
		panic(rows.Err())
	}
}

func (inspector *Inspector) checkWebVersion(item ItemWithSubKind) {
	scriptPath := fmt.Sprint(inspector.scriptsPath, "/", item.subKind, ".sh")
	if _, err := os.Stat(scriptPath); !os.IsNotExist(err) {
		cmd := exec.Command(scriptPath)
		cmd.Dir = strings.TrimSpace(item.subLoc)
		versionOutput, err := cmd.Output()
		pass := true
		if err != nil {
			if strings.Index(fmt.Sprint(err), "chdir") >= 0 {
				pass = false
				fmt.Printf("!chdir not found:%s\n", item.subLoc)
			} else {
				panic(err)
			}
		}
		if pass {
			versionString := strings.TrimSpace(string(versionOutput[:]))
			versionParts := strings.Split(versionString, "|")
			KindTitle := strings.TrimSpace(
				inspector.config.Section("inspector_scripts").Key(item.subKind).String(),
			)
			newItemVersion := ItemVersion{
				Domain:    item.id,
				Kind:      item.subKind,
				KindTitle: KindTitle,
				Path:      item.subLoc,
				Version:   versionParts[0],
			}
			if len(versionParts) == 2 {
				newItemVersion.PackagesVersions = versionParts[1]
			}
			inspector.itemVersions = append(inspector.itemVersions, newItemVersion)
		}
	}
}

func (inspector *Inspector) putItemVersionDoc(id string, rev string, hostname string) {
	itemVersionDoc := ItemVersionDoc{
		ID:         id,
		Rev:        rev,
		Hostname:   hostname,
		DocType:    "inspector",
		DocSubType: "web",
		Items:      inspector.itemVersions,
	}
	_, err := inspector.db.Put(context.TODO(), id, itemVersionDoc)
	if err != nil {
		panic(err)
	}
	// return itemVersionDoc
}

func (inspector *Inspector) printWebVersions() {
	for _, item := range inspector.itemVersions {
		versions := item.Version
		if item.PackagesVersions != "" {
			versions = versions + "; " + item.PackagesVersions
		}
		fmt.Printf("- %s:%s - %s\n  %s\n", item.Domain, item.Kind, item.KindTitle, versions)
	}
}

func (inspector *Inspector) saveWebVersions() {
	hostname, err := os.Hostname()
	if err != nil {
		panic(err)
	}
	id := fmt.Sprintf("%s-%s", "inspector", hostname)
	docRev, err := inspector.db.Rev(context.TODO(), id)
	if err != nil {
		if kivik.StatusCode(err) == kivik.StatusNotFound {
			inspector.putItemVersionDoc(id, "", hostname)
		} else {
			panic(err)
		}
	} else {
		inspector.putItemVersionDoc(id, docRev, hostname)
	}
}

func main() {
	inspector := Inspector{}
	inspector.Init()
	inspector.processWebItems()
	if inspector.isDryRunVerbose {
		inspector.printWebVersions()
	} else {
		inspector.saveWebVersions()
	}
}

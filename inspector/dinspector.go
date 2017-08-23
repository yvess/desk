package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os/exec"

	"github.com/flimzy/kivik"
	_ "github.com/flimzy/kivik/driver/couchdb"
	"gopkg.in/ini.v1"
)

type Worker struct {
	ID       string `json:"_id"`
	Rev      string `json:"_rev,omitempty"`
	Hostname string `json:"hostname"`
}

type ItemWithSubType struct {
	id      string
	kind    string
	subType string
	subLoc  string
}

type Inspector struct {
	config ini.File
	db     kivik.DB
}

func (inspector *Inspector) Init() {
	// config
	configPath := flag.String(
		"config",
		"/etc/desk/inspector.conf",
		"path of the inspector.conf config file (default: /etc/desk/inspector.conf)",
	)
	flag.Parse()
	fmt.Printf("configPath %s\n", *configPath)
	cfg, err := ini.Load(*configPath)
	if err != nil {
		panic(err)
	}
	inspector.config = *cfg

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

func (inspector *Inspector) GetDoc(docContainer interface{}, ID string) {
	row, err := inspector.db.Get(context.TODO(), ID)
	if err != nil {
		panic(err)
	}
	if err = row.ScanDoc(docContainer); err != nil {
		panic(err)
	}
}

func (inspector *Inspector) ProcessWebItems() {
	rows, err := inspector.db.Query(
		context.TODO(), "_design/desk_drawer", "_view/service_type",
		map[string]interface{}{"startkey": "[\"web\"]", "endkey": "[\"web\"]"},
	)
	if err != nil {
		panic(err)
	}
	for rows.Next() {
		var doc interface{}
		if err := rows.ScanValue(&doc); err != nil {
			panic(err)
		}
		//panic(doc)
		included_service_items := doc.(map[string]interface{})["included_service_items"]
		for _, itemFromJson := range included_service_items.([]interface{}) {
			itemMap := itemFromJson.(map[string]interface{})
			if itemMap["itemSubType"] != nil && itemMap["itemSubLoc"] != nil {
				item := ItemWithSubType{
					id:      itemMap["itemid"].(string),
					kind:    itemMap["itemType"].(string),
					subType: itemMap["itemSubType"].(string),
					subLoc:  itemMap["itemSubLoc"].(string),
				}
				inspector.CheckWebVersion(item)
			}
		}
	}
	if rows.Err() != nil {
		panic(rows.Err())
	}
}

func (inspector *Inspector) CheckWebVersion(item ItemWithSubType) {
	fmt.Printf("doc %s %s %s\n", item.id, item.subType, item.subLoc)
}

func main() {
	inspector := Inspector{}
	inspector.Init()

	var foremanWorker Worker
	inspector.GetDoc(&foremanWorker, "worker-foreman")
	fmt.Printf("The hostname is '%s'\n", foremanWorker.Hostname)

	out, err := exec.Command("date").Output()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("The date is %s\n", out)
	inspector.ProcessWebItems()
}

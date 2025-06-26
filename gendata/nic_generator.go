package main

import (
	"fmt"
	"github.com/Pallinder/go-randomdata"
	"github.com/gin-gonic/gin"
	"math"
	"net/http"
	"strings"
	"time"
)

func main() {

	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()
	r.GET("/v1/generator", generator)
	r.Run(":3000")
	
}

func generator(c *gin.Context) {
	layout := "2006-01-02"
	dqs := c.Query("date")
	provinces := []string{"Western", "Central", "Southern", "Northern", "Eastern", "North Western", "North Central", "Uva", "Sabaragahmuwa"}

	date, err := dateQueryHandler(dqs)
	if err != nil {
		sendErrorJsonGenerator(c, err, http.StatusBadRequest)
		return
	}

	sqs := c.Query("sex")
	sex, sas, err := sexQueryHandler(sqs)
	if err != nil {
		sendErrorJsonGenerator(c, err, http.StatusBadRequest)
		return
	}

	fdoy := time.Date(date.Year(), 1, 1, 0, 0, 0, 0, time.UTC)
	doy := int(math.Ceil(date.Sub(fdoy).Hours()/24) + 1)

	sn := randomdata.Number(0, 1000)
	if date.Year() >= 2000 {
		sn = randomdata.Number(0, 10000)
	}

	cd := randomdata.Number(0, 10)

	sdoy := doy
	if sex == false {
		sdoy += 500
	}

	onic := generateONIC(date.Year(), sdoy, sn, cd)
	osn := fmt.Sprintf("%03d", sn)
	if len(onic) != 10 {
		onic = ""
		osn = ""
	}

	nnic := generateNNIC(date.Year(), sdoy, sn, cd)
	nsn := fmt.Sprintf("%04d", sn)
	barcodeContent := fmt.Sprintf("NNIC:%s|DOB:%s|SEX:%s", nnic, date.Format(layout), sas)

	if len(nnic) != 12 {
		nnic = ""
		nsn = ""
		barcodeContent = ""
	}

	pn := randomdata.Number(0, 9)
	ps := fmt.Sprintf("%v Province", provinces[pn])

	c.JSON(http.StatusOK, gin.H{
		"status": true,
		"date":   date.Format(layout),
		"doy":    doy,
		"sn": gin.H{
			"old": osn,
			"new": nsn,
		},
		"cd":   cd,
		"sex":  sas,
		"onic": onic,
		"nnic": nnic,
		"province": gin.H{
			"number": pn + 1,
			"name":   ps,
		},
		"barcode": gin.H{
			"content": barcodeContent,
			"image":   "", // Flask backend generates actual image
		},
	})
}

func sendErrorJsonGenerator(c *gin.Context, err error, code int) {
	c.JSON(code, gin.H{
		"status": false,
		"error":  err.Error(),
		"code":   http.StatusText(code),
	})
}

func dateQueryHandler(dqs string) (time.Time, error) {
	layout := "2006-01-02"
	date := time.Now()
	var err error = nil

	if len(dqs) > 0 {
		date, err = time.Parse(layout, dqs)
	} else {
		db18 := time.Now().AddDate(-18, 0, 0).Format(layout)
		db118 := time.Now().AddDate(-118, 0, 0).Format(layout)
		date, err = time.Parse("Monday 2 Jan 2006", randomdata.FullDateInRange(db118, db18))
	}

	return date, err
}

func sexQueryHandler(sqs string) (bool, string, error) {
	sqs = strings.ToLower(sqs)

	switch sqs {
	case "m", "male":
		return true, "Male", nil
	case "f", "female":
		return false, "Female", nil
	case "":
		rs := randomdata.Boolean()
		rss := "Male"
		if rs == false {
			rss = "Female"
		}
		return rs, rss, nil
	default:
		return false, "", fmt.Errorf("Sex parameter can not be parsed.")
	}
}

func generateONIC(year int, doy int, sn int, cd int) string {
	if sn > 999 || year > 2000 {
		return ""
	}

	sy := year % 100
	ssy := fmt.Sprintf("%02d", sy)

	return fmt.Sprintf("%v%03d%03d%d%v", ssy, doy, sn, cd, "V")
}

func generateNNIC(year int, doy int, sn int, cd int) string {
	return fmt.Sprintf("%d%03d%04d%d", year, doy, sn, cd)
}

import React, {Component} from "react";
import {
  isAndroid,
  isIOS
} from "react-device-detect";

const aboutGlobalMap = <div>
    <img src={"/static/img/airsports_no_text.png"} style={{float: "right", width: "50px"}} alt={"Global logo"}/>
    <h2>Global map</h2><br/>
    <p>
        The global map shows an overview of ongoing and upcoming events, as well as all traffic currently using the
        tracking platform. By clicking on individual events the user can jump to the event details on the map and also
        to the competition tracking pages if they exist.
    </p>
    <p>
        The map is for entertainment use only, but we strive to keep the positions up-to-date for all the users who are
        actively tracking their aircraft position.
    </p>
    <p>
        <i className="mdi mdi-airplanemode-active" style={{color: "blue",  fontSSize: "28px"}}/> Active aircraft<br/>
        <i className="mdi mdi-airplanemode-active" style={{color: "blue",  fontSSize: "28px", opacity: 0.4}}/> &lt; 40 knots<br/>
        <i className="mdi mdi-airplanemode-active" style={{color: "grey",  fontSSize: "28px", opacity: 0.4}}/> &gt; 20 sec old
    </p>
    <p/>
    Take part in tracking your flights or competing in contests by downloading the Air Sports Live Tracking app
    from <a target={"_blank"}
            href='https://play.google.com/store/apps/details?id=no.airsports.android.livetracking&pcampaignid=pcampaignidMKT-Other-global-all-co-prtnr-py-PartBadge-Mar2515-1'>Google
    Play</a> or <a target={"_blank"}
                   href="https://apps.apple.com/us/app/air-sports-live-tracking/id1559193686?itsct=apps_box&amp;itscg=30200">Apple
    App Store</a>.
    <div className={"d-flex justify-content-around"}>
        {!isIOS?
        <div className={"p-2"}>
            <a target={"_blank"}
               href='https://play.google.com/store/apps/details?id=no.airsports.android.livetracking&pcampaignid=pcampaignidMKT-Other-global-all-co-prtnr-py-PartBadge-Mar2515-1'><img
                alt='Get it on Google Play' style={{height: "60px"}}
                src='https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png'/></a>
        </div>:null}
        {!isAndroid?
        <div className={"p-2"}>
            <a target={"_blank"}
               href="https://apps.apple.com/us/app/air-sports-live-tracking/id1559193686?itsct=apps_box&amp;itscg=30200"><img
                style={{height: "60px", padding: "8px"}}
                src="https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us??size=500x166&amp;releaseDate=1436918400&h=a41916586b4763422c974414dc18bad0"
                alt="Download on the App Store"/></a>
        </div>:null}
    </div>
    <div className="video-container">
        <iframe src="https://www.youtube.com/embed/UBiX8IQjIHw"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                frameBorder="0" allowFullScreen className="video"/>
    </div>
</div>

export default aboutGlobalMap

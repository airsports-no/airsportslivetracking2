import React, {Component} from "react";
import {connect} from "react-redux";
import {compareScore, contestantRankingTable, contestantShortForm, pz} from "../utilities";
import BootstrapTable from 'react-bootstrap-table-next';
import paginationFactory from 'react-bootstrap-table2-paginator';
import "bootstrap/dist/css/bootstrap.min.css"
import {CONTESTANT_DETAILS_DISPLAY} from "../constants/display-types";
import {
    displayOnlyContestantTrack,

    highlightContestantTrack,
    removeHighlightContestantTrack,
    setDisplay,
    showLowerThirds,
} from "../actions";
import {Loading} from "./basicComponents";
import {ProgressCircle, ProjectedScore} from "./contestantProgress";
import 'react-circular-progressbar/dist/styles.css';

var moment = require("moment");
var momentDurationFormatSetup = require("moment-duration-format");

function getTrackingStateBackgroundClass(state) {
    if (["Tracking", "Procedure turn"].includes(state)) return "greenBackground";
    if (["Backtracking", "Failed procedure turn"].includes(state)) return "redBackground"
    return ""
}

function calculateProjectedScore(score, progress) {
    if (progress <= 0) {
        return 99999
    }
    if (progress < 5) {
        return 99999
    }
    return (100 * score / progress)
}

const mapStateToProps = (state, props) => ({
    contestants: Object.keys(state.contestantData).map((key, index) => {
        return {
            track: state.contestantData[key].contestant_track,
            progress: state.contestantData[key].progress,
            initialLoading: state.initialLoadingContestantData[key],
            contestant: state.contestants[key]
        }
    }),
    displayExpandedTrackingTable: state.displayExpandedTrackingTable,
    highlight: state.highlightContestantTable
})


class ConnectedContestantRankTable extends Component {
    constructor(props) {
        super(props);
        this.rowStyle = this.rowStyle.bind(this)
        this.numberStyle = this.numberStyle.bind(this)
        this.handleContestantLinkClick = this.handleContestantLinkClick.bind(this)
        this.getStateFormat = this.getStateFormat.bind(this)
        this.selectedLine = null
        this.setHighlightedRef = element => {
            this.selectedLine = element;
        }

    }


    handleContestantLinkClick(contestantId) {
        this.props.setDisplay({displayType: CONTESTANT_DETAILS_DISPLAY, contestantId: contestantId})
        this.props.displayOnlyContestantTrack(contestantId)
        this.props.showLowerThirds(contestantId)
        this.props.removeHighlightContestantTrack(contestantId)
    }


    numberStyle(cell, row, rowIndex, colIndex) {
        return {backgroundColor: this.props.colourMap[row.contestantNumber]}
    }

    rowStyle(row, rowIndex) {
        return {backgroundColor: this.props.colourMap[row.contestantNumber]}
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (this.props.highlight.length === 1 && this.selectedLine) {
            // this.selectedLine.scrollIntoView({block: "center"})
        }
    }

    buildData() {
        const contestants = this.props.contestants.filter((contestant) => {
            return contestant != null && contestant.contestant !== undefined
        })
        contestants.sort(compareScore)
        return contestants.map((contestant, index) => {
            const progress = Math.min(100, Math.max(0, contestant.progress.toFixed(1)))
            return {
                key: contestant.contestant.id + "rack" + index,
                colour: "",
                contestantNumber: contestant.contestant.contestant_number,
                contestantId: contestant.contestant.id,
                rank: index + 1,
                progress: progress,
                name: contestantRankingTable(contestant.contestant),
                score: contestant.track.score,
                projectedScore: calculateProjectedScore(contestant.track.score, progress),
                currentState: contestant.initialLoading ? "Loading..." : contestant.track.current_state,
                finished: contestant.track.current_state === "Finished",
                initialLoading: contestant.initialLoading,
                lastGate: contestant.track.last_gate,
                lastGateTimeOffset: moment.duration(contestant.track.last_gate_time_offset, "seconds").format([
                    moment.duration(1, "second"),
                    moment.duration(1, "minute"),
                    moment.duration(1, "hour")
                ], "d [days] hh:mm:ss"),
                latestStatus: contestant.track.score_log.length > 0 ? contestant.track.score_log[contestant.track.score_log.length - 1] : ""
            }
        })
    }

    getStateFormat(cell, row) {
        if (row.initialLoading) {
            return <Loading/>
        }
        return <div>{cell}</div>
    }


    getTrackProgressFormat(cell, row) {

    }

    render() {
        const columns = [
            {
                dataField: "colour",
                text: "  ",
                style: this.numberStyle

            },
            {
                dataField: "rank",
                text: "#",
                // headerEvents: {
                //     onClick: (e, column, columnIndex) => {
                //         this.handleExpandHeaderClick()
                //     }
                // },
                classes: "align-middle",
                sort: true
            },
            {
                dataField: "contestantNumber",
                text: "#",
                hidden: true
            },
            {
                dataField: "contestantId",
                text: "",
                hidden: true
            },
            {
                dataField: "name",
                text: "CREW"
            },
            {
                dataField: "score",
                text: "SCORE",
                classes: "align-middle"
            },
            {
                dataField: "projectedScore",
                text: "EST",
                classes: "align-middle",
                style: (cell, row, rowIndex, colIndex) => {
                    return {color: "orange"}
                },
                formatter: (cell, row) => {
                    let value = cell.toFixed(0)
                    if (value === "99999") {
                        value = "--"
                    }
                    if (this.props.highlight.includes(row.contestantId)) {
                        return <span ref={this.setHighlightedRef}>{value}</span>
                    }
                    return value
                },
                sort: true,
                sortFunc: (a, b, order, dataField, rowA, rowB) => {
                    if (order === 'asc') {
                        return b - a;
                    }
                    return a - b; // desc
                }
            },
            {
                dataField: "progress",
                text: "LAP",
                formatter: (cell, row) => {
                    return <ProgressCircle progress={row.progress} finished={row.finished}/>
                },
                headerClasses: "text-center",
                style: (cell, row, rowIndex, colIndex) => {
                    return {width: 60 + 'px'}
                },
                classes: "align-middle"
            },
            {
                dataField: "currentState",
                text: "STATE",
                hidden: !this.props.displayExpandedTrackingTable,

                classes: function callback(cell, row, rowIndex, colIndex) {
                    return getTrackingStateBackgroundClass(cell)
                },
                // formatter: this.getStateFormat
            },
            {
                dataField: "latestStatus",
                text: "EVENT",
                hidden: true//!this.props.displayExpandedTrackingTable
            },
            {
                dataField: "lastGate",
                text: "GATE",
                hidden: !this.props.displayExpandedTrackingTable
            },
            {
                dataField: "lastGateTimeOffset",
                text: "OFFSET",
                hidden: !this.props.displayExpandedTrackingTable
            }
        ]

        const rowEvents = {
            onClick: (e, row, rowIndex) => {
                this.handleContestantLinkClick(row.contestantId)
            },
            onMouseEnter: (e, row, rowIndex) => {
                this.props.highlightContestantTrack(row.contestantId)
            },
            onMouseLeave: (e, row, rowIndex) => {
                this.props.removeHighlightContestantTrack(row.contestantId)
            }
        }

        const paginationOptions = {
            sizePerPage: 15,
            hideSizePerPage: true,
            hidePageListOnlyOnePage: true
        };
        const rowClasses = (row, rowIndex) => {
            if (this.props.highlight.includes(row.contestantId)) {
                return "selectedContestantRow"
            }
        }

        return <BootstrapTable keyField={"key"} data={this.buildData()} columns={columns}
                               rowClasses={rowClasses}
                               defaultSorted={[{dataField: "rank", order: "asc"}]}
                               classes={"table-dark"} wrapperClasses={"text-dark bg-dark"}
                               bootstrap4 striped hover condensed
                               bordered={false}//pagination={paginationFactory(paginationOptions)}
                               rowEvents={rowEvents}/>
    }
}

const
    ContestantRankTable = connect(mapStateToProps, {
        setDisplay,
        displayOnlyContestantTrack,
        showLowerThirds,
        highlightContestantTrack,
        removeHighlightContestantTrack
    })(ConnectedContestantRankTable)
export default ContestantRankTable
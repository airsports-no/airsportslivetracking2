import React, {Component} from "react";
import {connect} from "react-redux";
import {dispatchTraccarData, fetchContests, fetchContestsNavigationTaskSummaries} from "../../actions";
import TimePeriodEventList from "./timePeriodEventList";

export const mapStateToProps = (state, props) => ({
    contests: state.contests
})
export const mapDispatchToProps = {}

function sortContestTimes(a, b) {
    const startTimeA = new Date(a.start_time)
    const finishTimeA = new Date(a.finish_time)
    const startTimeB = new Date(b.start_time)
    const finishTimeB = new Date(b.finish_time)
    if (startTimeA < startTimeB) {
        return -1;
    }
    if (startTimeA > startTimeB) {
        return 1;
    }
    if (finishTimeA < finishTimeB) {
        return -1;
    }
    if (finishTimeA > finishTimeB) {
        return 1;
    }
    return 0;
}

class ConnectedGlobalEventList extends Component {
    constructor(props) {
        super(props)
    }

    handleManagementClick(){
        window.location.href = document.configuration.managementLink
    }


    render() {
        const now = new Date()
        let header=<div className={"card-header"}>Events</div>
        if (document.configuration.managementLink) {
            header = <div className={"card-header active"} onClick={()=>this.handleManagementClick()}>Events (management)</div>
        }
        const upcomingEvents = this.props.contests.filter((contest) => {
            const startTime = new Date(contest.start_time)
            const finishTime = new Date(contest.finish_time)
            if (startTime > now) {
                return contest
            }
        }).sort(sortContestTimes)
        const ongoingEvents = this.props.contests.filter((contest) => {
            const startTime = new Date(contest.start_time)
            const finishTime = new Date(contest.finish_time)
            if (finishTime > now && startTime < now) {
                return contest
            }
        }).sort(sortContestTimes)
        const earlierEvents = this.props.contests.filter((contest) => {
            const startTime = new Date(contest.start_time)
            const finishTime = new Date(contest.finish_time)
            if (finishTime < now) {
                return contest
            }
        }).sort(sortContestTimes)
        return <div>
            <div className={"card text-white bg-dark"}>
                {header}
                <div className={"card-body"}>
                    Ongoing events
                    <TimePeriodEventList contests={ongoingEvents}/>
                    Upcoming events
                    <TimePeriodEventList contests={upcomingEvents}/>
                    Past events
                    <TimePeriodEventList contests={earlierEvents}/>
                </div>
            </div>

        </div>
    }
}

const GlobalEventList = connect(mapStateToProps, mapDispatchToProps)(ConnectedGlobalEventList);
export default GlobalEventList;
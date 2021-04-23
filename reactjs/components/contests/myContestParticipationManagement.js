import React, {Component} from "react";
import {connect} from "react-redux";
import MyParticipatingEventsList from "./myParticipatingEventsList";
import UpcomingContestsSignupTable from "../upcomingContestsSignupTable";
import ContestRegistrationForm from "../contestRegistrationForm";
import {fetchMyParticipatingContests} from "../../actions";
import Navbar from "../navbar";

export const mapStateToProps = (state, props) => ({
    currentContestRegistration: state.currentContestRegistration,
    currentContestParticipation: state.currentContestParticipation,
    contests: state.contests,
    myParticipatingContests: state.myParticipatingContests
})
export const mapDispatchToProps = {
    fetchMyParticipatingContests
}


class ConnectedMyContestParticipationManagement extends Component {
    constructor(props) {
        super(props)
        this.state = {
            contest: null
        }
    }

    componentDidMount() {
        this.props.fetchMyParticipatingContests()
    }

    componentDidUpdate(prevProps) {
        // if (this.props.externalContestId) {
        //     this.setState({
        //         externalContest: this.props.filter((contest) => {
        //             return contest.id === this.props.externalContestId
        //         })
        //     })
        // }
    }


    render() {
        let contest = this.props.currentContestRegistration
        if (!contest && this.props.currentContestParticipation) {
            contest = this.props.currentContestParticipation.contest
        }
        let external = false
        let alreadyRegistered = false
        if (this.props.externalContestId) {
            if (!this.props.myParticipatingContests.find((contestTeam) => {
                return contestTeam.contest.id === this.props.externalContestId
            })) {
                contest = this.props.contests.find((contest) => {
                    return contest.id === this.props.externalContestId
                })
                if (contest) {
                    external = true
                }
            } else {
                alreadyRegistered = true
            }
        }
        return <div>
            <div className={"row"}>
                <div className={"col-4"}>
                    <h2>My upcoming contests</h2>
                    <MyParticipatingEventsList/>
                </div>
                <div className={"col-8"}>
                    {alreadyRegistered ? <h3>You are already registered for that contest</h3> : null}
                    {contest ?
                        <ContestRegistrationForm
                            contest={contest} external={external}
                            participation={this.props.currentContestParticipation}/> :
                        <UpcomingContestsSignupTable/>}
                </div>
            </div>
        </div>
    }
}

const MyContestParticipationManagement = connect(mapStateToProps,
    mapDispatchToProps)(ConnectedMyContestParticipationManagement);
export default MyContestParticipationManagement;
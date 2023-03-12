import React, {Component} from "react";
import {connect} from "react-redux";
import ContestDisplayGlobalMap from "./contestDisplayGlobalMap";

export const mapStateToProps = (state, props) => ({
    contests: state.contests
})
export const mapDispatchToProps = {}

class ConnectedContestsGlobalMap extends Component {
    constructor(props) {
        super(props)
    }

    render() {
        if (this.props.map !== null) {
            const now = new Date()
            const contests = this.props.contests.map((contest) => {
                if (contest.latitude !== 0 && contest.longitude !== 0 && new Date(contest.finish_time).getTime() > now.getTime())
                    return <ContestDisplayGlobalMap key={contest.id} map={this.props.map} contest={contest}/>
            })
            return <div>{contests}</div>
        }
        return null
    }
}

const ContestsGlobalMap = connect(mapStateToProps, mapDispatchToProps)(ConnectedContestsGlobalMap);
export default ContestsGlobalMap;
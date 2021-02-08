import {
    DISPLAY_ALL_TRACKS,
    DISPLAY_TRACK_FOR_CONTESTANT,
    EXCLUSIVE_DISPLAY_TRACK_FOR_CONTESTANT,
    GET_NAVIGATION_TASK_SUCCESSFUL,
    GET_CONTESTANT_DATA_SUCCESSFUL,
    HIDE_ALL_TRACKS,
    SET_DISPLAY,
    EXPAND_TRACKING_TABLE,
    SHRINK_TRACKING_TABLE,
    GET_CONTESTANT_DATA_REQUEST,
    GET_CONTESTANT_DATA_FAILED,
    INITIAL_LOADING_COMPLETE,
    INITIAL_LOADING,
    CHECK_FOR_NEW_CONTESTANTS_SUCCESSFUL,
    SHOW_LOWER_THIRDS,
    HIDE_LOWER_THIRDS,
    HIGHLIGHT_CONTESTANT,
    REMOVE_HIGHLIGHT_CONTESTANT,
    REMOVE_HIGHLIGHT_CONTESTANT_TABLE,
    HIGHLIGHT_CONTESTANT_TABLE,
    HIGHLIGHT_CONTESTANT_TRACK,
    REMOVE_HIGHLIGHT_CONTESTANT_TRACK,
    FULL_HEIGHT_TABLE,
    HALF_HEIGHT_TABLE, EXPLICITLY_DISPLAY_ALL_TRACKS, TRACCAR_DATA_RECEIVED
} from "../constants/action-types";
import {SIMPLE_RANK_DISPLAY} from "../constants/display-types";

const initialState = {
    navigationTask: {route: {waypoints: []}},
    contestantData: {},
    contestants: {},
    currentDisplay: {displayType: SIMPLE_RANK_DISPLAY},
    displayTracks: null,
    displayExpandedTrackingTable: false,
    displayFullHeightTrackingTable: false,
    isFetchingContestantData: {},
    initialLoadingContestantData: {},
    displayLowerThirds: null,
    highlightContestantTrack: [],
    highlightContestantTable: [],
    explicitlyDisplayAllTracks: false
};

function rootReducer(state = initialState, action) {
    if (action.type === SET_DISPLAY) {
        return Object.assign({}, state, {
            currentDisplay: action.payload
        })
    }
    if (action.type === GET_NAVIGATION_TASK_SUCCESSFUL) {
        // This has to match whatever is generated by track data for contestant
        /*{"contestant_id": contestant.pk, "latest_time": global_latest_time, "positions": positions,
            "annotations": annotations,
            "contestant_track": contestant_track, "more_data": more_data}*/
        let contestantData = {}
        let contestants = {}
        let initialLoading = {}
        action.payload.contestant_set.map((contestant) => {

            contestantData[contestant.id] = {
                latest_time: state.contestantData[contestant.id] ? state.contestantData[contestant.id].latest_time : "1970-01-01T00:00:00Z",
                positions: [],
                annotations: [],
                more_data: true,
                progress: state.contestantData[contestant.id] ? state.contestantData[contestant.id].progress : 0,
                contestant_track: contestant.contestanttrack
            }
            contestants[contestant.id] = contestant
            // initialLoading[contestant.id] = true
        })
        return Object.assign({}, state, {
            ...state,
            contestantData: contestantData,
            navigationTask: action.payload,
            contestants: contestants,
            // initialLoadingContestantData:initialLoading
        })
    }
    if (action.type === INITIAL_LOADING) {
        return Object.assign({}, state, {
            ...state,
            initialLoadingContestantData: {
                ...state.initialLoadingContestantData,
                [action.contestantId]: true
            }
        })
    }
    if (action.type === INITIAL_LOADING_COMPLETE) {
        return Object.assign({}, state, {
            ...state,
            initialLoadingContestantData: {
                ...state.initialLoadingContestantData,
                [action.contestantId]: false
            }
        })
    }
    if (action.type === GET_CONTESTANT_DATA_REQUEST) {
        return Object.assign({}, state, {
            ...state,
            isFetchingContestantData: {
                ...state.isFetchingContestantData,
                [action.id]: true
            }
        })
    }
    if (action.type === GET_CONTESTANT_DATA_FAILED) {
        return Object.assign({}, state, {
            ...state,
            isFetchingContestantData: {
                ...state.isFetchingContestantData,
                [action.id]: false
            }
        })
    }
    if (action.type === GET_CONTESTANT_DATA_SUCCESSFUL) {
        if (Object.keys(action.payload).length == 0) {
            return {
                ...state,
                isFetchingContestantData: {
                    ...state.isFetchingContestantData,
                    [action.payload.contestant_id]: false
                }
            }
        }
        return {
            ...state,
            contestantData: {
                ...state.contestantData,
                [action.payload.contestant_id]: {
                    annotations: action.payload.annotations,
                    positions: action.payload.positions,
                    progress: action.payload.progress !== undefined ? action.payload.progress : state.contestantData[action.payload.contestant_id].progress,
                    contestant_track: action.payload.contestant_track,
                    contestant_id: action.payload.contestant_id,
                    latest_time: action.payload.latest_time
                }
            },
            isFetchingContestantData: {
                ...state.isFetchingContestantData,
                [action.payload.contestant_id]: false
            }
        }
    }
    if (action.type === HIGHLIGHT_CONTESTANT_TABLE) {
        return Object.assign({}, state, {
            highlightContestantTable: state.highlightContestantTable.concat([action.contestantId])
        });
    }
    if (action.type === REMOVE_HIGHLIGHT_CONTESTANT_TABLE) {
        return Object.assign({}, state, {
            highlightContestantTable: state.highlightContestantTable.filter((id) => {
                return id !== action.contestantId
            })
        });
    }

    if (action.type === HIGHLIGHT_CONTESTANT_TRACK) {
        return Object.assign({}, state, {
            highlightContestantTrack: state.highlightContestantTrack.concat([action.contestantId])
        });
    }
    if (action.type === REMOVE_HIGHLIGHT_CONTESTANT_TRACK) {
        return Object.assign({}, state, {
            highlightContestantTrack: state.highlightContestantTrack.filter((id) => {
                return id !== action.contestantId
            })
        });
    }
    if (action.type === DISPLAY_TRACK_FOR_CONTESTANT) {
        let existingTracks = state.displayTrack;
        if (!existingTracks) {
            existingTracks = []
        }
        return Object.assign({}, state, {
            displayTracks: existingTracks.concat(action.payload.contestantIds)
        });
    }
    if (action.type === DISPLAY_ALL_TRACKS) {
        return Object.assign({}, state, {
            displayTracks: null
        });
    }

    if (action.type === EXPLICITLY_DISPLAY_ALL_TRACKS) {
        if (!state.displayTracks || state.displayTracks.length < Object.keys(state.contestants).length) {
            return Object.assign({}, state, {
                displayTracks: Object.keys(state.contestants).map((id) => {
                    return parseInt(id)
                }),
            });
        } else {
            return Object.assign({}, state, {
                displayTracks: null,
            })
        }
    }
    if (action.type === HIDE_ALL_TRACKS) {
        return Object.assign({}, state, {
            displayTracks: []
        });
    }
    if (action.type === EXCLUSIVE_DISPLAY_TRACK_FOR_CONTESTANT) {
        return Object.assign({}, state, {
            displayTracks: [action.payload.contestantId]
        });
    }
    if (action.type === EXPAND_TRACKING_TABLE) {
        return Object.assign({}, state, {
            displayExpandedTrackingTable: true
        });
    }
    if (action.type === SHRINK_TRACKING_TABLE) {
        return Object.assign({}, state, {
            displayExpandedTrackingTable: false
        });
    }
    if (action.type === FULL_HEIGHT_TABLE) {
        return Object.assign({}, state, {
            displayFullHeightTrackingTable: true
        });
    }
    if (action.type === HALF_HEIGHT_TABLE) {
        return Object.assign({}, state, {
            displayFullHeightTrackingTable: false
        });
    }
    if (action.type === SHOW_LOWER_THIRDS) {
        return Object.assign({}, state, {
            displayLowerThirds: action.contestantId
        });
    }
    if (action.type === HIDE_LOWER_THIRDS) {
        return Object.assign({}, state, {
            displayLowerThirds: null
        });
    }
    if (action.type === TRACCAR_DATA_RECEIVED) {
        let positions = {}
        action.data.map((position) => {
            const now = new Date()
            const deviceTime = new Date(position.deviceTime)
            if (now.getTime() - deviceTime.getTime() < 60 * 60 * 1000) {
                positions[position.deviceId] = position
            }
        })
        return Object.assign({}, state, {
            traccarPositions: positions
        });
    }
    return state;
}

export default rootReducer;
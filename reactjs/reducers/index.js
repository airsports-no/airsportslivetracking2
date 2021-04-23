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
    HALF_HEIGHT_TABLE,
    EXPLICITLY_DISPLAY_ALL_TRACKS,
    TRACCAR_DATA_RECEIVED,
    GET_CONTESTS_SUCCESSFUL,
    GLOBAL_MAP_ZOOM_FOCUS_CONTEST,
    DISPLAY_PAST_EVENTS_MODAL,
    DISPLAY_DISCLAIMER_MODAL,
    FETCH_DISCLAIMER,
    FETCH_DISCLAIMER_SUCCESSFUL,
    DISPLAY_ABOUT_MODAL,
    FETCH_MY_PARTICIPATING_CONTESTS_SUCCESSFUL,
    REGISTER_FOR_CONTEST,
    UPDATE_CONTEST_REGISTRATION, CANCEL_CONTEST_REGISTRATION, GET_CONTESTS, FETCH_MY_PARTICIPATING_CONTESTS
} from "../constants/action-types";
import {SIMPLE_RANK_DISPLAY} from "../constants/display-types";
import {
    CREATE_TASK_SUCCESSFUL,
    CREATE_TASK_TEST_SUCCESSFUL,
    DELETE_TASK_SUCCESSFUL,
    DELETE_TASK_TEST_SUCCESSFUL,
    GET_CONTEST_RESULTS_SUCCESSFUL,
    GET_CONTEST_TEAMS_LIST_SUCCESSFUL,
    GET_TASK_TESTS_SUCCESSFUL,
    GET_TASKS_SUCCESSFUL, HIDE_ALL_TASK_DETAILS, HIDE_TASK_DETAILS, PUT_TEST_RESULT_SUCCESSFUL,
    SHOW_TASK_DETAILS
} from "../constants/resultsServiceActionTypes";
import {fetchContestResults} from "../actions/resultsService";

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
    explicitlyDisplayAllTracks: false,
    contests: [],
    zoomContest: null,
    displayPastEventsModal: false,
    displayAboutModal: false,
    tasks: {},
    taskTests: {},
    contestResults: {},
    teams: null,
    visibleTaskDetails: {},
    disclaimer: "",
    myParticipatingContests: [],
    currentContestRegistration: null,
    loadingMyParticipation: false,
    loadingContests: false
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
                // latest_time: state.contestantData[contestant.id] ? state.contestantData[contestant.id].latest_time : "1970-01-01T00:00:00Z",
                latest_time: state.contestantData[contestant.id] ? state.contestantData[contestant.id].latest_time : "1970-01-01T00:00:00Z",
                positions: [],
                annotations: state.contestantData[contestant.id] ? state.contestantData[contestant.id].annotations : [],
                log_entries: state.contestantData[contestant.id] ? state.contestantData[contestant.id].log_entries : [],
                playing_cards: state.contestantData[contestant.id] ? state.contestantData[contestant.id].playing_cards : [],
                gate_scores: state.contestantData[contestant.id] ? state.contestantData[contestant.id].gate_scores : [],
                more_data: true,
                progress: state.contestantData[contestant.id] ? state.contestantData[contestant.id].progress : 0,
                // contestant_track: contestant.contestanttrack
                contestant_track: state.contestantData[contestant.id] ? state.contestantData[contestant.id].contestant_track : {
                    current_state: "Waiting...",
                    score: 0
                }
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

                    log_entries: action.payload.score_log_entries ? action.payload.score_log_entries : state.contestantData[action.payload.contestant_id].log_entries,
                    gate_scores: action.payload.gate_scores ? action.payload.gate_scores : state.contestantData[action.payload.contestant_id].gate_scores,
                    playing_cards: action.payload.playing_cards ? action.payload.playing_cards : state.contestantData[action.payload.contestant_id].playing_cards,

                    progress: action.payload.progress !== undefined ? action.payload.progress : state.contestantData[action.payload.contestant_id].progress,
                    contestant_track: action.payload.contestant_track ? action.payload.contestant_track : state.contestantData[action.payload.contestant_id].contestant_track,
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
    if (action.type === GET_CONTESTS) {
        return Object.assign({}, state, {
            loadingContests: true
        });
    }
    if (action.type === GET_CONTESTS_SUCCESSFUL) {
        return Object.assign({}, state, {
            contests: action.payload,
            loadingContests: false
        })
    }
    if (action.type === GLOBAL_MAP_ZOOM_FOCUS_CONTEST) {

        return Object.assign({}, state, {
            zoomContest: action.payload
        })
    }
    if (action.type === DISPLAY_PAST_EVENTS_MODAL) {
        return Object.assign({}, state, {
            displayPastEventsModal: action.payload
        })
    }
    if (action.type === DISPLAY_DISCLAIMER_MODAL) {
        return Object.assign({}, state, {
            displayDisclaimerModal: action.payload
        })
    }
    if (action.type === DISPLAY_ABOUT_MODAL) {
        return Object.assign({}, state, {
            displayAboutModal: action.payload
        })
    }
    if (action.type === FETCH_DISCLAIMER_SUCCESSFUL) {
        return Object.assign({}, state, {
            disclaimer: action.payload
        })

    }
    if (action.type === GET_CONTEST_RESULTS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            contestResults: {
                ...state.contestResults,
                [action.contestId]: {
                    ...state.contestResults[action.contestId],
                    results: action.payload
                }
            }
        })
    }
    if (action.type === CREATE_TASK_SUCCESSFUL) {
        const remaining = state.tasks[action.contestId].filter((task) => {
            return task.id !== action.payload.id
        })
        return Object.assign({}, state, {
            ...state,
            tasks: {
                ...state.tasks,
                [action.contestId]: remaining.concat([action.payload])
            }
        })
    }
    if (action.type === CREATE_TASK_TEST_SUCCESSFUL) {
        const remaining = state.taskTests[action.contestId].filter((taskTest) => {
            return taskTest.id !== action.payload.id
        })
        return Object.assign({}, state, {
            ...state,
            taskTests: {
                ...state.taskTests,
                [action.contestId]: remaining.concat([action.payload])
            }
        })
    }
    if (action.type === DELETE_TASK_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            tasks: {
                ...state.tasks,
                [action.contestId]: state.tasks[action.contestId].filter((task) => {
                    return task.id !== action.payload
                })
            }
        })
    }
    if (action.type === DELETE_TASK_TEST_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            taskTests: {
                ...state.taskTests,
                [action.contestId]: state.taskTests[action.contestId].filter((taskTest) => {
                    return taskTest.id !== action.payload
                })
            }
        })
    }
    if (action.type === GET_TASKS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            tasks: {
                ...state.tasks,
                [action.contestId]: action.payload
            }
        })
    }
    if (action.type === GET_TASK_TESTS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            taskTests: {
                ...state.taskTests,
                [action.contestId]: action.payload
            }
        })
    }
    if (action.type === GET_CONTEST_TEAMS_LIST_SUCCESSFUL) {
        let teamsMap = state.teams ? state.teams : {}
        action.payload.map((team) => {
            teamsMap[team.id] = team
        })
        return Object.assign({}, state, {
            ...state,
            teams: teamsMap,
        })
    }
    if (action.type === SHOW_TASK_DETAILS) {
        return Object.assign({}, state, {
            ...state,
            visibleTaskDetails: {
                ...state.visibleTaskDetails,
                [action.taskId]: true
            }
        })
    }
    if (action.type === HIDE_TASK_DETAILS) {
        return Object.assign({}, state, {
            ...state,
            visibleTaskDetails: {
                ...state.visibleTaskDetails,
                [action.taskId]: false
            }
        })
    }
    if (action.type === HIDE_ALL_TASK_DETAILS) {
        return Object.assign({}, state, {
            ...state,
            visibleTaskDetails: {}
        })
    }
    if (action.type===PUT_TEST_RESULT_SUCCESSFUL){
        fetchContestResults(action.contestId)
        return state
    }
    if (action.type === GET_CONTEST_RESULTS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            contestResults: {
                ...state.contestResults,
                [action.contestId]: {
                    ...state.contestResults[action.contestId],
                    results: action.payload
                }
            }
        })
    }
    if (action.type === CREATE_TASK_SUCCESSFUL) {
        const remaining = state.tasks[action.contestId].filter((task) => {
            return task.id !== action.payload.id
        })
        return Object.assign({}, state, {
            ...state,
            tasks: {
                ...state.tasks,
                [action.contestId]: remaining.concat([action.payload])
            }
        })
    }
    if (action.type === CREATE_TASK_TEST_SUCCESSFUL) {
        const remaining = state.taskTests[action.contestId].filter((taskTest) => {
            return taskTest.id !== action.payload.id
        })
        return Object.assign({}, state, {
            ...state,
            taskTests: {
                ...state.taskTests,
                [action.contestId]: remaining.concat([action.payload])
            }
        })
    }
    if (action.type === DELETE_TASK_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            tasks: {
                ...state.tasks,
                [action.contestId]: state.tasks[action.contestId].filter((task) => {
                    return task.id !== action.payload
                })
            }
        })
    }
    if (action.type === DELETE_TASK_TEST_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            taskTests: {
                ...state.taskTests,
                [action.contestId]: state.taskTests[action.contestId].filter((taskTest) => {
                    return taskTest.id !== action.payload
                })
            }
        })
    }
    if (action.type === GET_TASKS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            tasks: {
                ...state.tasks,
                [action.contestId]: action.payload
            }
        })
    }
    if (action.type === GET_TASK_TESTS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            taskTests: {
                ...state.taskTests,
                [action.contestId]: action.payload
            }
        })
    }
    if (action.type === GET_CONTEST_TEAMS_LIST_SUCCESSFUL) {
        let teamsMap = state.teams ? state.teams : {}
        action.payload.map((team) => {
            teamsMap[team.id] = team
        })
        return Object.assign({}, state, {
            ...state,
            teams: teamsMap,
        })
    }
    if (action.type === SHOW_TASK_DETAILS) {
        return Object.assign({}, state, {
            ...state,
            visibleTaskDetails: {
                ...state.visibleTaskDetails,
                [action.taskId]: true
            }
        })
    }
    if (action.type === HIDE_TASK_DETAILS) {
        return Object.assign({}, state, {
            ...state,
            visibleTaskDetails: {
                ...state.visibleTaskDetails,
                [action.taskId]: false
            }
        })
    }
    if (action.type === HIDE_ALL_TASK_DETAILS) {
        return Object.assign({}, state, {
            ...state,
            visibleTaskDetails: {}
        })
    }
    if (action.type === PUT_TEST_RESULT_SUCCESSFUL) {
        fetchContestResults(action.contestId)
        return state
    }
    if (action.type === FETCH_MY_PARTICIPATING_CONTESTS) {
        return Object.assign({}, state, {
            loadingMyParticipation: true
        });
    }
    if (action.type === FETCH_MY_PARTICIPATING_CONTESTS_SUCCESSFUL) {
        return Object.assign({}, state, {
            ...state,
            myParticipatingContests: action.payload,
            loadingMyParticipation: false
        })
    }
    if (action.type === REGISTER_FOR_CONTEST) {
        return Object.assign({}, state, {
            ...state,
            currentContestRegistration: action.payload
        })

    }

    if (action.type === UPDATE_CONTEST_REGISTRATION) {
        return Object.assign({}, state, {
            ...state,
            currentContestParticipation: action.payload
        })

    }
    if (action.type === CANCEL_CONTEST_REGISTRATION) {
        return Object.assign({}, state, {
            ...state,
            currentContestParticipation: null,
            currentContestRegistration: null
        })

    }

    return state;
}

export default rootReducer;
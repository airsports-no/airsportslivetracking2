import React, {Component} from "react";
import {Button, Col, Container, Form, Modal} from "react-bootstrap";
import axios from 'axios'
import {ErrorMessage, Formik} from 'formik';
import {connect} from "react-redux";
import * as yup from 'yup';
import {fetchMyParticipatingContests} from "../actions";
import {withRouter} from "react-router-dom";
import DatePicker from "react-datepicker";

import "react-datepicker/dist/react-datepicker.css";


axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
const _ = require('lodash');
const mapStateToProps = (state, props) => ({})

class ConnectedSelfRegistrationForm extends Component {
    constructor(props) {
        super(props)
        this.schema = yup.object().shape({
            starting_point_time: yup.string().required(),
        });
    }

    handleSuccess() {
        this.props.fetchMyParticipatingContests()
        this.props.history.push("/participation/myparticipation/" + this.props.participation.id + "/")

    }

    componentDidMount() {
    }


    render() {
        let initialValues = {
            starting_point_time: new Date(),
            wind_speed: 0,
            wind_direction: 0
        }

        const formikProps = {
            initialValues: initialValues,
            validationSchema: this.schema,
            onSubmit: (formValues, {setSubmitting, setStatus, setErrors}) => {
                formValues.starting_point_time.setSeconds(0)
                let data = {
                    starting_point_time: formValues.starting_point_time.toISOString(),
                    contest_team: this.props.participation.id,
                    wind_speed: formValues.wind_speed,
                    wind_direction: formValues.wind_direction
                }
                console.log("submit", data);
                setSubmitting(true);
                axios.put("/api/v1/contests/" + this.props.participation.contest.id + "/navigationtasks/" + this.props.navigationTask.pk + "/contestant_self_registration/", data).then((res) => {
                    setStatus("Registration successful")
                    this.handleSuccess()
                }).catch((e) => {
                    console.error(e);
                    console.log(e);
                    const errors = _.get(e, ["response", "data"])
                    if (Array.isArray(errors)) {
                        setErrors({api: errors})
                    } else {
                        setErrors(errors)
                    }
                }).finally(() => {
                    setSubmitting(false);
                })

            }
        }

        return (
            <div>
                <h2>Set starting time for {this.props.navigationTask.name}</h2>

                <Formik {...formikProps}>
                    {props => (
                        <Form onSubmit={props.handleSubmit} onAbort={() => this.props.history.push("/participation/")}>
                            <Form.Group>
                                <Form.Label>Starting point time</Form.Label>
                                <DatePicker
                                    selected={props.values.starting_point_time}
                                    name={"starting_point_time"}
                                    onChange={value => props.setFieldValue("starting_point_time", value)}
                                    showTimeSelect
                                    timeFormat="HH:mm"
                                    timeIntervals={1}
                                    timeCaption="time"
                                    dateFormat="MMMM d, yyyy hh:mm"
                                />
                                {/*<DateTimePicker value={props.values.starting_point_time}*/}
                                {/*            name={"starting_point_time"} disableClock clearIcon={null} showLeadingZeros={true}*/}
                                {/*            onChange={value => props.setFieldValue("starting_point_time", value)}*/}
                                {/*/>*/}
                                <ErrorMessage name={"starting_point_time"} component={"div"}/>
                            </Form.Group>
                            <Form.Row>
                                <Col>
                                    <Form.Label>Wind speed</Form.Label>
                                    <Form.Control name={"wind_speed"} type={"number"} placeholder={"Speed"}
                                                  onChange={props.handleChange}
                                                  defaultValue={props.initialValues.wind_speed}/>
                                    <ErrorMessage name={"wind_speed"} component={"div"}/>
                                </Col>
                                <Col>
                                    <Form.Label>Wind direction</Form.Label>
                                    <Form.Control name={"wind_direction"} type={"number"} placeholder={"Direction"}
                                                  onChange={props.handleChange}
                                                  defaultValue={props.initialValues.wind_direction}/>
                                    <ErrorMessage name={"wind_direction"} component={"div"}/>
                                </Col>
                            </Form.Row>
                            <Form.Row>
                                <Button variant="primary" type="submit" disabled={props.isSubmitting}>
                                    Register
                                </Button>
                                <Button variant={"danger"} type={"button"}
                                        onClick={() => {
                                            this.props.history.push("/participation/myparticipation/" + this.props.participation.id + "/")
                                        }}>Cancel</Button>
                                {props.errors && _.has(props.errors, ["api"]) &&
                                <div className="text-danger">{_.get(props.errors, ["api"])}</div>}
                                {props.status && <div className="text-success">{props.status}</div>}
                            </Form.Row>
                        </Form>)}
                </Formik>
            </div>
        )
    }

}

const SelfRegistrationForm = withRouter(connect(mapStateToProps,
    {
        fetchMyParticipatingContests
    }
)(ConnectedSelfRegistrationForm))
export default SelfRegistrationForm
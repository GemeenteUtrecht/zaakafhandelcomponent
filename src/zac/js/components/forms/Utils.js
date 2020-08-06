import React from 'react';
import PropTypes from 'prop-types';


const ErrorList = ({ errors=[] }) => {
    return (
        <React.Fragment>
            { errors.map((error, index) => <div key={index} className="input__error">{ error }</div>) }
        </React.Fragment>
    );
};


const Wrapper = ({ errors=[], children }) => {
    const hasErrors = errors && errors.length > 0;
    const className = "input";
    if (hasErrors) {
        className += " input--invalid";
    }
    return (
        <div className={className}>
            {children}
        </div>
    );
};


const SubmitRow = ({ text="Bevestigen" }) => {
    return (
        <div className="input">
            <button type="submit" className="btn btn--primary">{text}</button>
        </div>
    );
};

SubmitRow.propTypes = {
    text: PropTypes.string,
};


export { ErrorList, Wrapper, SubmitRow };

import React from 'react';
import PropTypes from 'prop-types';
import classnames from 'classnames';

const ErrorList = ({ errors = [] }) => (
    <>
        { errors.map((error, index) => <div key={index} className="input__error">{ error }</div>) }
    </>
);

const Wrapper = ({ errors = [], children }) => {
    const hasErrors = errors && errors.length > 0;
    return (
        <div
            className={classnames(
                'input',
                { 'input--invalid': hasErrors },
            )}
        >
            {children}
        </div>
    );
};

const SubmitRow = ({
    text = 'Bevestigen',
    btnModifier = 'primary',
    onClick = null,
    isDisabled = false,
}) => {
    const btnClassName = `btn btn--${btnModifier}`;
    return (
        <div className="input">
            <button
                type="submit"
                className={btnClassName}
                onClick={(event) => (onClick ? onClick(event) : null)}
                disabled={isDisabled}
            >
                {text}
            </button>
        </div>
    );
};

/**
 * Get the first non-falsy attribute from an array of objects.
 */
const getAttr = (attr='', objects=[], defaultVal='') => {
    for (let obj of objects) {
        if (!obj) {
            continue;
        }
        if (!obj[attr]) {
            continue;
        }
        return obj[attr];
    }
    return defaultVal;
};

const extractErrors = (errList) => {
    return errList.map( err => err.msg );
};

const isEmpty = (obj) => {
    if (!obj) {
        return true;
    }
    return Object.keys(obj).length === 0;
};


SubmitRow.propTypes = {
    text: PropTypes.string,
    btnModifier: PropTypes.string,
    onClick: PropTypes.func,
    isDisabled: PropTypes.bool,
};

export { ErrorList, Wrapper, SubmitRow, getAttr, extractErrors, isEmpty };

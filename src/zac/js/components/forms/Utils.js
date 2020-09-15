import React from 'react';
import PropTypes from 'prop-types';

const ErrorList = ({ errors = [] }) => (
    <>
        { errors.map((error, index) => <div key={index} className="input__error">{ error }</div>) }
    </>
);

const Wrapper = ({ errors = [], children }) => {
    const hasErrors = errors && errors.length > 0;
    let className = 'input';
    if (hasErrors) {
        className += ' input--invalid';
    }
    return (
        <div className={className}>
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

SubmitRow.propTypes = {
    text: PropTypes.string,
    btnModifier: PropTypes.string,
    onClick: PropTypes.func,
    isDisabled: PropTypes.bool,
};

export { ErrorList, Wrapper, SubmitRow };

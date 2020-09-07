import React from "react";
import PropTypes from "prop-types";


const ManagementForm = ({ prefix, initial, total, minNum, maxNum }) => {
    return (
        <React.Fragment>
            <input type="hidden" name={`${prefix}-TOTAL_FORMS`} defaultValue={ total } />
            <input type="hidden" name={`${prefix}-INITIAL_FORMS`} defaultValue={ initial } />
            <input type="hidden" name={`${prefix}-MIN_NUM_FORMS`} defaultValue={ minNum } />
            <input type="hidden" name={`${prefix}-MAX_NUM_FORMS`} defaultValue={ maxNum } />
        </React.Fragment>
    )
};


ManagementForm.propTypes = {
    prefix: PropTypes.string.isRequired,
    initial: PropTypes.number.isRequired,
    total: PropTypes.number.isRequired,
    minNum: PropTypes.number.isRequired,
    maxNum: PropTypes.number.isRequired,
};


export { ManagementForm };

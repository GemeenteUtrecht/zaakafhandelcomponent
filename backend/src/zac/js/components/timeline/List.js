import React from 'react';
import PropTypes from 'prop-types';


const List = ({ children }) => {
    return (
        <ul className="list list--timeline">
            {children}
        </ul>
    );
};

List.propTypes = {
    children: PropTypes.node,
};


export { List };

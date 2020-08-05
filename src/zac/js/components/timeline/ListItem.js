import React from 'react';
import PropTypes from 'prop-types';


const ListItem = ({ time, children, exactTime=null, headingLevel=3 }) => {
    const Heading = `h${headingLevel}`;
    return (
        <li className="list__item">
            <Heading className="list__item-heading">
                <time title={exactTime ?? null}>{time}</time>
            </Heading>
            <p>
                {children}
            </p>
        </li>
    );
};

ListItem.propTypes = {
    time: PropTypes.string.isRequired,
    children: PropTypes.node.isRequired,
    exactTime: PropTypes.string,
    headingLevel: PropTypes.oneOf([2, 3, 4, 5, 6]),
};


export { ListItem };

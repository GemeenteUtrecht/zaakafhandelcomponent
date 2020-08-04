import React, { useState } from 'react';
import PropTypes from 'prop-types';


const Tab = ({ index, title, onClick, active=false }) => {
    const target = `tab-content-${index}`;
    const id = `tab-${index}`;

    let className = 'tab__tab';
    if (active) {
        className += ' tab__tab--active';
    }

    return (
        <li role="tab"aria-controls={target} className={className}>
            <a href={`#${target}`} onClick={onClick}>{title}</a>
        </li>
    );
};

Tab.propTypes = {
    index: PropTypes.number.isRequired,
    title: PropTypes.node.isRequired,
    onClick: PropTypes.func.isRequired,
    active: PropTypes.bool,
};


const TabContentWrapper = ({index, children, active=false}) => {
    if (!active) return null;

    const id = `tab-content-${index}`;
    const label = `tab-${index}`;

    return (
        <section className="tab__pane tab__pane--active"id={id} aria-labelledby={label} role="tabpanel">
            {children}
        </section>
    );
};

TabContentWrapper.propTypes = {
    index: PropTypes.number.isRequired,
    children: PropTypes.node,
    active: PropTypes.bool,
};


const TabList = ({ children }) => {

    const [activeTab, setActiveTab] = useState(0);

    return (
        <React.Fragment>
            <ul className="tab tab--inline" role="tablist">
                { children.map((child, index) => (
                    <Tab
                        key={index}
                        index={index}
                        title={child.props.title}
                        onClick={ (event) => {
                            event.preventDefault();
                            setActiveTab(index);
                        } }
                        active={activeTab === index}
                    />
                ) ) }
            </ul>

            <div className="tab__content tab__content--inline">
                { children.map( (child, index) => (
                    <TabContentWrapper key={index} index={index} active={activeTab === index}>{child}</TabContentWrapper>
                ) ) }
            </div>
        </React.Fragment>
    );
};

TabList.propTypes = {
    children: PropTypes.arrayOf(PropTypes.element), // and specifically, TabContent
};


const TabContent = ({ title, children }) => {
    return (
        <React.Fragment>{ children }</React.Fragment>
    );
};


TabContent.propTypes = {
    title: PropTypes.node.isRequired,
    children: PropTypes.node,
};


export { TabList, TabContent };

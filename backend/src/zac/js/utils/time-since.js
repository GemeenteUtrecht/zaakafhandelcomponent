import moment from "moment";


const timeSince = (timestamp) => {
    return moment(timestamp).fromNow();
};


const timeUntil = timeSince;


export { timeSince, timeUntil };

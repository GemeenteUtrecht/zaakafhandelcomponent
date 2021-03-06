import { jsonScriptToVar } from '../utils/json-script';

const ID = 'openUrl';

const main = () => {
    if (!document.getElementById(ID)) {
        return;
    }

    const openUrl = jsonScriptToVar(ID);
    if (!openUrl) {
        return;
    }

    window.open(openUrl, '_blank');
};

main();

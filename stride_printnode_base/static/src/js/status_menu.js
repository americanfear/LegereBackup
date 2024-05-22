/** @odoo-module **/

import ajax from 'web.ajax';
import rpc from 'web.rpc';
import session from 'web.session';

import { registry } from '@web/core/registry';

import WORKSTATION_DEVICES from './constants';

const systrayRegistry = registry.category('systray');
const MANAGER_GROUP = 'stride_printnode_base.printnode_security_group_manager';

export class PrintnodeStatusMenu extends owl.Component {
    setup() {
        this.state = owl.useState({
            limits: [],
            devices: [],
            isManager: false,
        });
    }

    async willStart() {
        // We check if current user has Manager group to make some elements of status menu
        // visible only for managers
        const groupCheckPromise = session.user_has_group(MANAGER_GROUP).then(
            this._loadContent.bind(this));

        return groupCheckPromise;
    }

    async _loadContent(isManager) {
        this.state.isManager = isManager;

        if (isManager) {
            const limitsPromise = rpc.query({ model: 'printnode.account', method: 'get_limits' });

           

            return Promise.all(
                [limitsPromise]
            ).then(this._loadedCallback.bind(this));
        }
    }

    _loadedCallback([limits]) {
        // Process limits
        this.state.limits = limits;
    }

    _capitalizeWords(str) {
        const words = str.split(" ");
        let capitalizedWords = words.map(w => w[0].toUpperCase() + w.substr(1));
        return capitalizedWords.join(' ');
    }

    _onStatusMenuShow() {
        /*
        Update workstation devices each time user clicks on the status menu
        */
        // Clean old information about workstation devices
        this.state.devices = [];

        const devicesInfo = Object.fromEntries(
            WORKSTATION_DEVICES
                .map(n => [n, localStorage.getItem('stride_printnode_base.' + n)])  // Two elements array
                .filter(i => i[1]) // Skip empty values
        );

        const devicesPromise = rpc.query({
            model: 'res.users',
            method: 'validate_device_id',
            kwargs: { devices: devicesInfo }
        });

        devicesPromise.then((data) => {
            // Process workstation devices
            const devices = WORKSTATION_DEVICES.map(
                device => {
                    // Remove printnode_ and _id from the of string
                    let deviceName = device.substring(10, device.length - 3).replace(/_/g, ' ');

                    // Return pairs (type, name)
                    return [this._capitalizeWords(deviceName), data[device]];
                }
            );

            this.state.devices = devices;
        });
    }
}

Object.assign(PrintnodeStatusMenu, {
    props: {},
    template: 'stride_printnode_base.StatusMenu',
});

systrayRegistry.add('stride_printnode_base.StatusMenu', {
    Component: PrintnodeStatusMenu,
});
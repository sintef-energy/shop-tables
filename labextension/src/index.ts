import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

/**
 * Initialization data for the jupyterlab-itables extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-itables:plugin',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('JupyterLab extension jupyterlab-itables is activated!');
  }
};

export default plugin;
